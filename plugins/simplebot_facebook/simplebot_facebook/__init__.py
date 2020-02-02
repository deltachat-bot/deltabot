# -*- coding: utf-8 -*-
from enum import IntEnum
from threading import Thread, Event, BoundedSemaphore
import gettext
import json
import os
import sqlite3

from fbchat import Client, Message, ThreadType, FBchatException, ImageAttachment, FileAttachment, AudioAttachment, VideoAttachment
from simplebot import Plugin, PluginCommand, PluginFilter
import bs4
import requests


class Status(IntEnum):
    DISABLED = 0
    ENABLED = 1


class FacebookBridge(Plugin):

    name = 'FB Messenger'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        save = False
        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('delay'):
            cls.cfg['delay'] = '10'
            save = True
        if not cls.cfg.get('max-size'):
            cls.cfg['max-size'] = '1048576'
            save = True
        if not cls.cfg.get('pool-size'):
            cls.cfg['pool-size'] = '10'
            save = True
        if save:
            cls.bot.save_config()

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'facebook.db'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_facebook', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.pool_size = cls.cfg.getint('pool-size')
        cls.pool = BoundedSemaphore(value=cls.pool_size)
        cls.code_events = dict()
        cls.worker = Thread(target=cls.listen_to_fb)
        cls.worker.deactivated = Event()
        cls.worker.start()

        cls.description = _('Facebook Messenger bridge')

        cls.long_description = _(
            'Allows to chat with your friends from Facebook right from Delta Chat.\nIt is recommended you enable 2FA in your Facebook account for this plugin to work correctly, otherwise your account could get disabled.')
        cls.filters = [PluginFilter(cls.process_messages)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand('/fb/login', ['<user>', '<password>'],
                          _('Login in Facebook and start receiving messages'), cls.login_cmd),
            PluginCommand('/fb/code', ['<code>'],
                          _('Send verification code'), cls.code_cmd),
            PluginCommand('/fb/password', ['<password>'],
                          _('Update your password'), cls.password_cmd),
            PluginCommand('/fb/logout', [],
                          _('Logout from Facebook, your credentials and all Facebook groups will be forgotten by the bot'), cls.logout_cmd),
            PluginCommand('/fb/disable', [],
                          _('Ignore messages from Facebook until the account is enabled again'), cls.disable_cmd),
            PluginCommand('/fb/enable', [],
                          _('Start receiving messages from Facebook again'), cls.enable_cmd),
            PluginCommand('/fb/mute', [],
                          _('Stop receiving messages from the Facebook group this command is sent'), cls.mute_cmd),
            PluginCommand('/fb/unmute', [],
                          _('Start receiving messages again from the Facebook group this command is sent'), cls.unmute_cmd),
            PluginCommand('/fb/more', [],
                          _('Every time you send this command, up to 20 more Facebook chats will be loaded in Delta Chat'), cls.more_cmd),
            PluginCommand('/fb/buddylist', [],
                          _('Sends the buddy list'), cls.buddylist_cmd),
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
            cls.db.commit(
                'UPDATE users SET status=? WHERE addr=?', (Status.DISABLED, addr))
            code_ev = Event()
            cls.code_events[addr] = code_ev
            cls.bot.get_chat(addr).send_text(
                _('A verification code should have been sent to you, use /fb/code to send the code'))
            if code_ev.wait(60*20):
                del cls.code_events[addr]
                return code_ev.code
            if addr in cls.code_events and cls.code_events[addr] is code_ev:
                del cls.code_events[addr]
            raise ValueError('Verification timed out.')

        u = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        onlogin.user = None
        try:
            onlogin.user = FBUser(
                u['username'], u['password'], u['cookie'], _on2fa)
            cookie = json.dumps(onlogin.user.getSession())
            if onlogin.is_set():
                cls.db.commit(
                    'UPDATE users SET cookie=?, status=? WHERE addr=?', (cookie, Status.ENABLED, addr))
            else:
                cls.db.commit(
                    'UPDATE users SET cookie=? WHERE addr=?', (cookie, addr))
        except FBchatException as ex:
            cls.db.commit(
                'UPDATE users SET status=? WHERE addr=?', (Status.DISABLED, addr))
            cls.bot.logger.exception(ex)
            cls.bot.get_chat(addr).send_text(
                _('Failed to login in Facebook, try enabling 2FA for your account and check your password is correct'))
        finally:
            onlogin.set()

    @classmethod
    def _create_group(cls, user, t, addr):
        name = t.name if t.name else _('(NO NAME)')
        g = cls.bot.create_group('🇫 ' + name, [addr])
        cls.db.insert_group((g.id, t.uid, t.type.value, addr, Status.ENABLED))

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
            g.set_profile_image(file_name)

        g.send_text(_('Name: {}').format(name))

        return g

    @classmethod
    def buddylist_cmd(cls, ctx):
        sender = ctx.msg.get_sender_contact()
        onlogin = Event()
        cls._login(onlogin, sender.addr)
        if onlogin.user is not None:
            r = onlogin.user._state._session.get(
                'https://m.facebook.com/buddylist.php')
            soup = bs4.BeautifulSoup(r.text, 'html.parser').find(id='root')
            text = ''
            for img in soup('img')[1:]:
                if img['width'] == '7' and img['height'] == '14':
                    status = '✅'
                else:
                    status = '📴'
                name = img.find_parent('tr').a.string
                text += '{} {}\n'.format(status, name)
            cls.bot.get_chat(sender).send_text(text)

    @classmethod
    def login_cmd(cls, ctx):
        def create_chats(addr):
            onlogin = Event()
            cls._login(onlogin, addr)
            user = onlogin.user
            if user is not None:
                for t in user.fetchThreadList(limit=20):
                    cls._create_group(user, t, addr)

        addr = ctx.msg.get_sender_contact().addr
        uname, passwd = ctx.text.split(maxsplit=1)
        old_user = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if not (old_user and old_user['cookie']):
            cls.db.insert_user((addr, uname, passwd, None, Status.DISABLED))
            Thread(target=create_chats, args=(addr,), daemon=True).start()
        else:
            cls.bot.get_chat(ctx.msg).send_text(
                _('You are already logged in'))

    @classmethod
    def password_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        chat = cls.bot.get_chat(ctx.msg)
        cls.db.commit(
            'UPDATE users SET password=? WHERE addr=?', (ctx.text, addr))
        chat.send_text(_('Password updated'))

    @classmethod
    def code_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        chat = cls.bot.get_chat(ctx.msg)
        if addr in cls.code_events:
            cls.code_events[addr].code = ctx.text
            cls.code_events[addr].set()
        else:
            chat.send_text(_('Unexpected verification'))

    @classmethod
    def logout_cmd(cls, ctx):
        contact = ctx.msg.get_sender_contact()
        addr = contact.addr
        ids = cls.db.execute(
            'SELECT group_id FROM groups WHERE addr=?', (addr,))
        me = cls.bot.get_contact()
        for gid in ids:
            g = cls.bot.get_chat(gid[0])
            if g is not None:
                try:
                    g.remove_contact(me)
                except ValueError as ex:
                    cls.bot.logger.exception(ex)
        cls.db.delete_user(addr)
        cls.bot.get_chat(contact).send_text(
            _('You have logged out from facebook'))

    @classmethod
    def disable_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        chat = cls.bot.get_chat(ctx.msg)
        cls.db.commit('UPDATE users SET status=? WHERE addr=?',
                      (Status.DISABLED, addr))
        chat.send_text(
            _('Account disabled'))

    @classmethod
    def enable_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        chat = cls.bot.get_chat(ctx.msg)
        cls.db.commit('UPDATE users SET status=? WHERE addr=?',
                      (Status.ENABLED, addr))
        chat.send_text(_('Account enabled'))

    @classmethod
    def mute_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        chat = cls.bot.get_chat(ctx.msg)
        cls.db.commit('UPDATE groups SET status=? WHERE group_id=? AND addr=?',
                      (Status.DISABLED, chat.id, addr))
        chat.send_text(_('Group muted'))

    @classmethod
    def unmute_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        chat = cls.bot.get_chat(ctx.msg)
        cls.db.commit('UPDATE groups SET status=? WHERE group_id=? AND addr=?',
                      (Status.ENABLED, chat.id, addr))
        chat.send_text(_('Group unmuted'))

    @classmethod
    def more_cmd(cls, ctx):
        def create_chats(addr):
            onlogin = Event()
            cls._login(onlogin, addr)
            user = onlogin.user
            if user is not None:
                threads = [t[0] for t in cls.db.execute(
                    'SELECT thread_id FROM groups WHERE addr=?', (addr,))]
                new_threads = set()
                before = None
                while True:
                    tlist = user.fetchThreadList(limit=20, before=before)
                    for t in tlist:
                        if t.uid not in threads:
                            if len(new_threads) == 20:
                                break
                            new_threads.add(t)
                    if len(new_threads) == 20 or len(tlist) < 20 or tlist[-1].last_message_timestamp in (None, before):
                        break
                    before = tlist[-1].last_message_timestamp
                for t in new_threads:
                    cls._create_group(user, t, addr)

        addr = ctx.msg.get_sender_contact().addr
        u = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if not u:
            cls.bot.get_chat(ctx.msg).send_text(
                _('You are not logged in'))
            return

        Thread(target=create_chats, args=(addr,), daemon=True).start()

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        group = cls.db.execute(
            'SELECT * FROM groups WHERE group_id=?', (chat.id,), 'one')
        if group is None:
            return
        ctx.processed = True
        addr = ctx.msg.get_sender_contact().addr
        u = cls.db.execute(
            'SELECT * FROM users WHERE addr=?', (addr,), 'one')
        if u['status'] == Status.DISABLED:
            chat.send_text(
                _('Your account is disabled, use /fb/enable to enable it.'))
            return
        if group['status'] == Status.DISABLED:
            cls.db.commit(
                'UPDATE groups SET status=? WHERE group_id=?', (Status.ENABLED, chat.id))

        Thread(target=cls._send_dc2fb, args=(
            group, ctx.text, ctx.msg.filename), daemon=True).start()

    @classmethod
    def _send_dc2fb(cls, g, text, filename):
        if g['addr'] in cls.code_events:
            cls.bot.logger.warning(
                'Tried to send message before code verification')
            return
        onlogin = Event()
        cls._login(onlogin, g['addr'])
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
    def _send_fb2dc(cls, user, addr):
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
                if row['status'] == Status.DISABLED:
                    continue
                g = cls.bot.get_chat(row['group_id'])
                if g is None:
                    members = []
                else:
                    members = g.get_contacts()
                if me not in members or len(members) != 2:
                    cls.db.commit(
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
                if msg.author == user.uid:
                    continue
                attachments = []
                if msg.sticker:
                    attachments.append(msg.sticker.url)
                elif msg.attachments:
                    for a in msg.attachments:
                        if type(a) in (ImageAttachment, VideoAttachment):
                            attachments.append(a.preview_url)
                        elif type(a) in (FileAttachment, AudioAttachment):
                            attachments.append(a.url)
                elif not msg.text:
                    cls.bot.logger.warning('Unsuported message, ignored.')
                    return

                text = msg.text if msg.text else ''
                if thread_type == ThreadType.GROUP:
                    if msg.author not in names:
                        names[msg.author] = user.fetchUserInfo(msg.author)[
                            msg.author].name
                    text = '{}:\n{}'.format(names[msg.author], text)
                if text:
                    g.send_text(text)

                max_size = cls.cfg.getint('max-size')
                for url in attachments:
                    file_name = os.path.basename(url).split('?')[
                        0].split('#')[0].lower()
                    file_path = cls.bot.get_blobpath(file_name)
                    with requests.get(url, stream=True) as r:
                        chunks = b''
                        size = 0
                        for chunk in r.iter_content(chunk_size=10240):
                            chunks += chunk
                            size += len(chunk)
                            if size > max_size:
                                break
                        else:
                            with open(file_path, 'wb') as fd:
                                fd.write(chunks)
                            g.send_file(file_path)

    @classmethod
    def listen_to_fb(cls):

        def _task(addr):
            with cls.pool:
                try:
                    onlogin = Event()
                    Thread(target=cls._login, args=(
                        onlogin, addr), daemon=True).start()
                    onlogin.wait(30)
                    if onlogin.user is None:
                        return
                    cls._send_fb2dc(onlogin.user, addr)
                except Exception as ex:
                    cls.bot.logger.exception(ex)

        while True:
            if cls.worker.deactivated.is_set():
                return
            cls.bot.logger.debug('Checking Facebook')
            for addr in map(lambda u: u[0], cls.db.execute('SELECT addr FROM users WHERE status=?', (Status.ENABLED,))):
                if cls.worker.deactivated.is_set():
                    return
                with cls.pool:
                    Thread(target=_task, args=(addr,)).start()
            for i in range(cls.pool_size):
                cls.pool.acquire()
            for i in range(cls.pool_size):
                cls.pool.release()
            cls.worker.deactivated.wait(cls.cfg.getint('delay'))


class FBUser(Client):
    def __init__(self, username, password, cookie, on_2fa):
        user_agent = ('Mozilla/5.0 (X11; Ubuntu; Linux x86_64; '
                      'rv:60.0) Gecko/20100101 Firefox/60.0')
        self.on_2fa = on_2fa
        if cookie is not None:
            cookie = json.loads(cookie)
        super().__init__(username, password, session_cookies=cookie,
                         user_agent=user_agent, max_tries=1)

    def on2FACode(self):
        return self.on_2fa()


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS users 
                (addr TEXT,
                username TEXT NOT NULL,
                password TEXT NOT NULL,
                cookie TEXT,
                status INTEGER NOT NULL,
                PRIMARY KEY(addr))''')
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS groups 
                (group_id INTEGER,
                thread_id TEXT NOT NULL,
                thread_type INTEGER NOT NULL,
                addr TEXT NOT NULL REFERENCES users(addr),
                status INTEGER NOT NULL,
                PRIMARY KEY(group_id))'''
            )

    def execute(self, statement, args=(), get='all'):
        r = self.db.execute(statement, args)
        return r.fetchall() if get == 'all' else r.fetchone()

    def commit(self, statement, args=(), get='all'):
        with self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def insert_user(self, user):
        self.execute('INSERT OR REPLACE INTO users VALUES (?,?,?,?,?)', user)

    def insert_group(self, group):
        self.execute('INSERT INTO groups VALUES (?,?,?,?,?)', group)

    def delete_user(self, addr):
        self.execute('DELETE FROM groups WHERE addr=?', (addr,))
        self.execute('DELETE FROM users WHERE addr=?', (addr,))

    def close(self):
        self.db.close()
