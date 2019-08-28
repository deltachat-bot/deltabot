# -*- coding: utf-8 -*-
from threading import Thread, RLock, Event
import functools
import gettext
import json
import os
import sqlite3

from fbchat import Client, Message, ThreadType
from simplebot import Plugin


GST_DISABLED = 0
GST_ENABLED = 1
UST_DISABLED = 0
UST_ENABLED = 1


class FacebookBridge(Plugin):

    name = 'FB Messenger'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'facebook.db'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_facebook', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.code_events = dict()
        cls.worker = Thread(target=cls.listen_to_fb)
        cls.worker.deactivated = Event()
        cls.worker.start()

        cls.description = _('Facebook Messenger bridge')

        cls.long_description = _(
            'Allows to chat with your friends from Facebook right from Delta Chat.\nIt is recommended you enable 2FA authentication in your Facebook account.')
        cls.filters = [cls.process_messages]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            ('/fb/login', ['<user>', '<password>'],
             _('Login in Facebook and start receiving messages'), cls.login_cmd),
            ('/fb/code', ['<code>'],
             _('Send verification code'), cls.code_cmd),
            ('/fb/password', ['<password>'],
             _('Update your password'), cls.password_cmd),
            ('/fb/logout', [],
             _('Logout from Facebook, your credentials and all Facebook groups will be forgotten by the bot'), cls.logout_cmd),
            ('/fb/disable', [],
             _('Ignore messages from Facebook until the account is enabled again'), cls.disable_cmd),
            ('/fb/enable', [],
             _('Start receiving messages from Facebook again'), cls.enable_cmd),
            ('/fb/mute', [],
             _('Stop receiving messages from the Facebook group this command is sent'), cls.mute_cmd),
            ('/fb/unmute', [],
             _('Start receiving messages again from the Facebook group this command is sent'), cls.unmute_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.worker.deactivated.set()
        cls.worker.join()
        cls.db.close()

    @classmethod
    def login_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        uname, passwd = arg.split(maxsplit=1)
        passwd = passwd.rstrip()
        old_user = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if old_user is None:
            cls.db.insert_user((addr, uname, passwd, None, UST_ENABLED))
        else:
            cls.bot.get_chat(msg).send_text(
                _('You are already logged in'))

    @classmethod
    def password_cmd(cls, msg, password):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE users SET password=? WHERE addr=?', (addr,))
        chat.send_text(_('Password updated'))

    @classmethod
    def code_cmd(cls, msg, code):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        if addr in cls.code_events:
            cls.code_events[addr].code = code
            cls.code_events[addr].set()
        else:
            chat.send_text(_('Unexpected verification'))

    @classmethod
    def logout_cmd(cls, msg, arg):
        contact = msg.get_sender_contact()
        addr = contact.addr
        ids = cls.db.execute(
            'SELECT group_id FROM groups WHERE addr=?', (addr,))
        me = cls.bot.get_contact()
        for gid in ids:
            g = cls.bot.get_chat(gid[0])
            try:
                g.remove_contact(me)
            except ValueError as ex:
                cls.bot.logger.exception(ex)
        cls.db.delete_user(addr)
        cls.bot.get_chat(contact).send_text(
            _('You have logged out from facebook'))

    @classmethod
    def disable_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE users SET status=? WHERE addr=?',
                       (UST_DISABLED, addr))
        chat.send_text(
            _('Account disabled, to enable again use /fb/enable'))

    @classmethod
    def enable_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE users SET status=? WHERE addr=?',
                       (UST_ENABLED, addr))
        chat.send_text(_('Account enabled'))

    @classmethod
    def mute_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE groups SET status=? WHERE group_id=? AND addr=?',
                       (GST_DISABLED, chat.id, addr))
        chat.send_text(_('Group muted, to unmute use /fb/unmute'))

    @classmethod
    def unmute_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE groups SET status=? WHERE group_id=? AND addr=?',
                       (GST_ENABLED, chat.id, addr))
        chat.send_text(_('Group unmuted'))

    @classmethod
    def on_2fa(cls, addr):
        cls.db.execute(
            'UPDATE users SET status=? WHERE addr=?', (UST_DISABLED, addr))
        user = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        code_ev = Event()
        cls.code_events[addr] = code_ev
        cls.bot.get_chat(addr).send_text(
            _('A verification code should have been sent to you, use /fb/code to send the code'))
        code_ev.wait()
        del cls.code_events[addr]
        return code_ev.code

    @classmethod
    def process_messages(cls, msg, text):
        chat = cls.bot.get_chat(msg)
        group = cls.db.execute(
            'SELECT * FROM groups WHERE group_id=?', (chat.id,), 'one')
        if group is None:
            return False
        elif not text:
            chat.send_text(_('Only text messages are supported'))
            return False

        addr = msg.get_sender_contact().addr
        u = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if u['status'] == UST_DISABLED:
            chat.send_text(
                _('Your account is disabled, use /fb/enable to enable it.'))
            return
        if group['status'] == GST_DISABLED:
            cls.db.execute(
                'UPDATE groups SET status=? WHERE group_id=? AND addr=?', (GST_ENABLED, chat.id, addr))

        Thread(target=cls._send_text, args=(
            u, group, addr, text), daemon=True).start()
        return True

    @classmethod
    def _send_text(cls, u, g, addr, text):
        if addr in cls.code_events:
            cls.bot.logger.warning(
                'Tried to send message before code verification')
            return
        user = FBUser(u['username'], u['password'], u['cookie'],
                      functools.partial(cls.on_2fa, addr))
        user.send_text(g['thread_id'], ThreadType(g['thread_type']), text)

    @classmethod
    def listen_to_fb(cls):
        while True:
            if cls.worker.deactivated.is_set():
                return
            cls.bot.logger.debug('Checking Facebook')
            for u in cls.db.execute('SELECT * FROM users WHERE status=?', (UST_ENABLED,)):
                if cls.worker.deactivated.is_set():
                    return
                try:
                    user = FBUser(u['username'], u['password'], u['cookie'],
                                  functools.partial(cls.on_2fa, u['addr']))
                    cls.db.execute('UPDATE users SET cookie=?, status=? WHERE addr=?', (json.dumps(
                        user.getSession()), UST_ENABLED, u['addr']))
                    for t_id in user.fetchUnread():
                        if cls.worker.deactivated.is_set():
                            return
                        gid = cls.db.execute(
                            'SELECT group_id FROM groups WHERE thread_id=? AND addr=?', (t_id, u['addr']), 'one')
                        if gid is None:
                            t = user.fetchThreadInfo(t_id)[t_id]
                            g = cls.bot.create_group(
                                '[F] ' + t.name, [u['addr']])
                            g.send_text('welcome to facebook ponk')
                            cls.db.insert_group(
                                (g.id, t_id, t.type.value, u['addr'], GST_ENABLED))
                        else:
                            g = cls.bot.get_chat(gid[0])
                        # TODO: get unread messages and send them and mark as read
                except Exception as ex:
                    cls.bot.logger.exception(ex)
                    cls.db.execute(
                        'UPDATE users SET status=? WHERE addr=?', (UST_DISABLED, u['addr']))
            cls.worker.deactivated.wait(10)


class FBUser(Client):
    def __init__(self, username, password, cookie, on_2fa):
        user_agent = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
        self.on_2fa = on_2fa
        if cookie is not None:
            cookie = json.loads(cookie)
        super().__init__(username, password, session_cookies=cookie,
                         user_agent=user_agent, max_tries=3)

    def on2FACode(self):
        return self.on_2fa()

    def send_text(self, thread_id, thread_type, text):
        self.send(Message(text=text), thread_id=thread_id,
                  thread_type=ThreadType(thread_type))


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = RLock()
        with self.db:
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS users 
                (addr TEXT NOT NULL,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                cookie TEXT,
                status INTEGER NOT NULL,
                PRIMARY KEY(addr))''')
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS groups 
                (group_id INTEGER NOT NULL,
                thread_id TEXT NOT NULL,
                thread_type INTEGER NOT NULL,
                addr TEXT NOT NULL REFERENCES users(addr),
                status INTEGER NOT NULL,
                PRIMARY KEY(group_id))'''
            )

    def execute(self, statement, args=(), get='all'):
        with self.lock, self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def insert_user(self, user):
        self.execute('INSERT INTO users VALUES (?,?,?,?,?)', user)

    def insert_group(self, group):
        self.execute('INSERT INTO groups VALUES (?,?,?,?,?)', group)

    def delete_user(self, addr):
        self.execute('DELETE FROM groups WHERE addr=?', (addr,))
        self.execute('DELETE FROM users WHERE addr=?', (addr,))

    def close(self):
        self.db.close()
