# -*- coding: utf-8 -*-
from threading import Thread, RLock, Event
import functools
import gettext
import json
import os
import sqlite3

from fbchat import Client, Message, ThreadType, FBchatException, ImageAttachment
from simplebot import Plugin
import deltachat as dc
import requests


G_DISABLED = 0
G_ENABLED = 1
U_DISABLED = 0
U_ENABLED = 1


class FacebookBridge(Plugin):

    name = 'FB Messenger'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('delay'):
            cls.cfg['delay'] = '10'
            cls.bot.save_config()

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
            'Allows to chat with your friends from Facebook right from Delta Chat.\nIt is recommended you enable 2FA in your Facebook account for this plugin to work correctly, otherwise your account could get disabled.')
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
    def _login(cls, onlogin, addr):
        def _on2fa():
            onlogin.set()
            cls.db.execute(
                'UPDATE users SET status=? WHERE addr=?', (U_DISABLED, addr))
            code_ev = Event()
            cls.code_events[addr] = code_ev
            cls.bot.get_chat(addr).send_text(
                _('A verification code should have been sent to you, use /fb/code to send the code'))
            code_ev.wait(60*60)
            del cls.code_events[addr]
            return code_ev.code

        u = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        onlogin.user = None
        try:
            onlogin.user = FBUser(
                u['username'], u['password'], u['cookie'], _on2fa)
            cookie = json.dumps(onlogin.user.getSession())
            if onlogin.is_set():
                cls.db.execute(
                    'UPDATE users SET cookie=?, status=? WHERE addr=?', (cookie, U_ENABLED, addr))
            else:
                cls.db.execute(
                    'UPDATE users SET cookie=? WHERE addr=?', (cookie, addr))
        except FBchatException as ex:
            cls.db.execute(
                'UPDATE users SET status=? WHERE addr=?', (U_DISABLED, addr))
            cls.bot.logger.exception(ex)
            cls.bot.get_chat(addr).send_text(
                _('Failed to login in Facebook, try enabling 2FA for your account and check your password is correct'))
        finally:
            onlogin.set()

    @classmethod
    def _create_group(cls, user, t, addr):
        name = t.name if t.name else _('(NO NAME)')
        g = cls.bot.create_group('[F] ' + name, [addr])
        cls.db.insert_group((g.id, t.uid, t.type.value, addr, G_ENABLED))
        g.send_text(_('Name: {}').format(name))

        if t.photo:
            r = requests.get(t.photo)
            content_type = r.headers.get('content-type', '').lower()
            if 'image/png' in content_type:
                file_name = 'group-img.png'
            elif 'image/jpeg' in content_type:
                file_name = 'group-img.jpg'
            else:
                file_name = os.path.basename(t.photo).split('?')[
                    0].split('#')[0].lower()
            file_name = cls.bot.get_blobpath(file_name)
            with open(file_name, 'wb') as fd:
                fd.write(r.content)
            dc.capi.lib.dc_set_chat_profile_image(
                cls.bot.account._dc_context, g.id, dc.account.as_dc_charpointer(file_name))
        return g

    @classmethod
    def login_cmd(cls, msg, arg):
        def create_chats(onlogin, t, addr):
            t.join()
            user = onlogin.user
            if user is not None:
                for t in user.fetchThreadList(limit=20):
                    cls._create_group(user, t, addr)

        addr = msg.get_sender_contact().addr
        uname, passwd = arg.split(maxsplit=1)
        passwd = passwd.rstrip()
        old_user = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if not old_user:
            cls.db.insert_user((addr, uname, passwd, None, U_DISABLED))
            onlogin = Event()
            t = Thread(target=cls._login, args=(
                onlogin, addr), daemon=True)
            t.start()
            Thread(target=create_chats, args=(
                onlogin, t, addr), daemon=True).start()
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
                       (U_DISABLED, addr))
        chat.send_text(
            _('Account disabled'))

    @classmethod
    def enable_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE users SET status=? WHERE addr=?',
                       (U_ENABLED, addr))
        chat.send_text(_('Account enabled'))

    @classmethod
    def mute_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE groups SET status=? WHERE group_id=? AND addr=?',
                       (G_DISABLED, chat.id, addr))
        chat.send_text(_('Group muted'))

    @classmethod
    def unmute_cmd(cls, msg, arg):
        addr = msg.get_sender_contact().addr
        chat = cls.bot.get_chat(msg)
        cls.db.execute('UPDATE groups SET status=? WHERE group_id=? AND addr=?',
                       (G_ENABLED, chat.id, addr))
        chat.send_text(_('Group unmuted'))

    @classmethod
    def process_messages(cls, msg, text):
        chat = cls.bot.get_chat(msg)
        group = cls.db.execute(
            'SELECT * FROM groups WHERE group_id=?', (chat.id,), 'one')
        if group is None:
            return False
        addr = msg.get_sender_contact().addr
        u = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if u['status'] == U_DISABLED:
            chat.send_text(
                _('Your account is disabled, use /fb/enable to enable it.'))
            return True
        if group['status'] == G_DISABLED:
            cls.db.execute(
                'UPDATE groups SET status=? WHERE group_id=? AND addr=?', (G_ENABLED, chat.id, addr))

        Thread(target=cls._send_dc2fb, args=(
            group, addr, text, msg.filename), daemon=True).start()
        return True

    @classmethod
    def _send_dc2fb(cls, g, addr, text, filename):
        if addr in cls.code_events:
            cls.bot.logger.warning(
                'Tried to send message before code verification')
            return
        onlogin = Event()
        cls._login(onlogin, addr)
        if onlogin.user is not None:
            try:
                thread_type = ThreadType(g['thread_type'])
                msg = Message(text) if text else None
                if filename:
                    onlogin.user.sendLocalFiles(
                        [filename], message=msg, thread_id=g['thread_id'], thread_type=thread_type)
                elif msg:
                    onlogin.user.send(msg, thread_id=g['thread_id'],
                                      thread_type=thread_type)
                else:
                    cls.bot.logger.warning(
                        'No file or text given, skipping message')
            except FBchatException as ex:
                cls.bot.logger.exception(ex)

    @classmethod
    def _send_new_messages(cls, user, addr):
        me = cls.bot.get_contact()
        for t_id in user.fetchUnread():
            if cls.worker.deactivated.is_set():
                return
            row = cls.db.execute(
                'SELECT group_id, thread_type, status FROM groups '
                'WHERE thread_id=? AND addr=?', (t_id, addr), 'one')
            if row is None:
                t = user.fetchThreadInfo(t_id)[t_id]
                g = cls._create_group(user, t, addr)
                thread_type = t.type
            else:
                if row['status'] == G_DISABLED:
                    continue
                g = cls.bot.get_chat(row['group_id'])
                members = g.get_contacts()
                if me not in members or len(members) != 2:
                    cls.db.execute(
                        'DELETE FROM groups WHERE group_id=?', (g.id,))
                    continue
                thread_type = ThreadType(row['thread_type'])
            messages = []
            before = None
            while True:
                msgs = [m for m in user.fetchThreadMessages(
                    thread_id=t_id, limit=10, before=before) if not m.is_read]
                messages.extend(msgs)
                if len(msgs) != 10:
                    break
                before = msgs[-1].timestamp
            user.markAsRead(t_id)
            names = dict()
            for msg in reversed(messages):
                if thread_type == ThreadType.GROUP:
                    if msg.author not in names:
                        names[msg.author] = user.fetchUserInfo(msg.author)[
                            msg.author].name
                    text = '{}:\n'.format(names[msg.author])
                else:
                    text = ''
                if msg.text:
                    g.send_text(text+msg.text)
                    return
                if msg.sticker:
                    images = [msg.sticker.url]
                elif msg.attachments:
                    images = []
                    for a in msg.attachments:
                        if type(a) is ImageAttachment:
                            images.append(a.preview_url)
                else:
                    cls.bot.logger.warning('Unsuported message, ignored.')
                    return
                if text:
                    g.send_text(text)
                for img_url in images:
                    r = requests.get(img_url)
                    file_name = os.path.basename(img_url).split('?')[
                        0].split('#')[0].lower()
                    file_path = cls.bot.get_blobpath(file_name)
                    with open(file_path, 'wb') as fd:
                        fd.write(r.content)
                    g.send_image(file_path)

    @classmethod
    def listen_to_fb(cls):
        while True:
            if cls.worker.deactivated.is_set():
                return
            cls.bot.logger.debug('Checking Facebook')
            for addr in map(lambda u: u[0], cls.db.execute('SELECT addr FROM users WHERE status=?', (U_ENABLED,))):
                if cls.worker.deactivated.is_set():
                    return
                try:
                    onlogin = Event()
                    Thread(target=cls._login, args=(
                        onlogin, addr), daemon=True).start()
                    onlogin.wait()
                    if onlogin.user is None:
                        continue
                    cls._send_new_messages(onlogin.user, addr)
                except Exception as ex:
                    cls.bot.logger.exception(ex)
            cls.worker.deactivated.wait(cls.cfg.getint('delay'))


class FBUser(Client):
    def __init__(self, username, password, cookie, on_2fa):
        user_agent = ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; '
                      'rv:60.0) Gecko/20100101 Firefox/60.0')
        self.on_2fa = on_2fa
        if cookie is not None:
            cookie = json.loads(cookie)
        super().__init__(username, password, session_cookies=cookie,
                         user_agent=user_agent, max_tries=3)

    def on2FACode(self):
        return self.on_2fa()


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
