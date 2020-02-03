# -*- coding: utf-8 -*-
from threading import Thread, Event
import asyncio
import gettext
import os
import re
import sqlite3

from simplebot import Plugin, PluginCommand, PluginFilter
from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError, IqTimeout

import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)-8s %(message)s')

FTYPES = {
    'image/png': 'png',
    'image/gif': 'gif',
    'image/jpeg': 'jpg'
}
nick_re = re.compile(r'[a-zA-Z0-9]{1,30}$')


class BridgeXMPP(Plugin):

    name = 'XMPP Bridge'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        save = False
        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('nick'):
            cls.cfg['nick'] = 'SimpleBot'
            save = True
        if save:
            cls.bot.save_config()

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_xmpp', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'xmpp.db'))

        cls.xmpp = XMPP(cls)
        cls.xmpp.connect()
        cls.worker = Thread(target=cls.listen_to_xmpp)
        cls.worker.start()
        cls.xmpp.connected.wait()

        cls.description = _('A bridge between Delta Chat and XMPP network.')
        cls.filters = [PluginFilter(cls.process_messages)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand(
                '/xmpp/join', ['<jid>'], _('Join to the given XMPP channel'), cls.join_cmd),
            PluginCommand('/xmpp/nick', ['[nick]'],
                          _('Set your nick or display your current nick if no new nick is given'), cls.nick_cmd),
            PluginCommand('/xmpp/members', [],
                          _('Show group memeber list'), cls.members_cmd),
            PluginCommand('/xmpp/remove', ['[nick]'],
                          _('Remove the member with the given nick from the group, if no nick is given remove yourself'), cls.remove_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def get_nick(cls, addr):
        r = cls.db.execute(
            'SELECT nick from nicks WHERE addr=?', (addr,)).fetchone()
        if r:
            return r[0]
        else:
            i = 1
            while True:
                nick = 'User{}'.format(i)
                r = cls.db.execute(
                    'SELECT nick FROM nicks WHERE nick=?', (nick,)).fetchone()
                if not r:
                    cls.db.execute(
                        'INSERT OR REPLACE INTO nicks VALUES (?,?)', (addr, nick))
                    break
                i += 1
            return nick

    @classmethod
    def get_channels(cls):
        for r in cls.db.execute('SELECT jid FROM channels'):
            yield r[0]

    @classmethod
    def get_cchats(cls, jid):
        me = cls.bot.get_contact()
        chats = []
        invalid_chats = []
        old_chats = cls.db.execute(
            'SELECT id FROM cchats WHERE channel=?', (jid,))
        for r in old_chats:
            chat = cls.bot.get_chat(r[0])
            if chat is None:
                cls.db.execute('DELETE FROM cchats WHERE id=?', (r[0],))
                continue
            contacts = chat.get_contacts()
            if me not in contacts or len(contacts) == 1:
                invalid_chats.append(chat)
            else:
                chats.append(chat)
        for chat in invalid_chats:
            cls.db.execute('DELETE FROM cchats WHERE id=?', (chat.id,))
            chat.remove_contact(me)
        if not chats:
            cls.db.execute('DELETE FROM channels WHERE jid=?', (jid,))
        return chats

    @classmethod
    def listen_to_xmpp(cls):
        cls.xmpp.process(forever=False)

    @classmethod
    def wait(cls, coro):
        return asyncio.run_coroutine_threadsafe(
            coro, cls.xmpp.loop).result()

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        r = cls.db.execute(
            'SELECT channel from cchats WHERE id=?', (chat.id,)).fetchone()
        if not r:
            return

        ctx.processed = True
        sender = ctx.msg.get_sender_contact()
        nick = cls.get_nick(sender.addr)

        if sender not in chat.get_contacts():
            return

        text = '{}[dc]:\n{}'.format(nick, ctx.text)
        if ctx.msg.filename:
            coro = cls.xmpp['xep_0363'].upload_file(
                ctx.msg.filename, timeout=10)
            url = cls.wait(coro)
            text += '\n{}'.format(url)

        cls.xmpp.send_message(r[0], text, mtype='groupchat')
        for g in cls.get_cchats(r[0]):
            if g.id != chat.id:
                g.send_text(text)

    @classmethod
    def xmpp2dc(cls, msg):
        for g in cls.get_cchats(msg['mucroom']):
            g.send_text('{0[mucnick]}[xmpp]:\n{0[body]}'.format(msg))

    @classmethod
    def nick_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        addr = ctx.msg.get_sender_contact().addr
        new_nick = ' '.join(ctx.text.split())
        if new_nick:
            if new_nick == addr:
                cls.db.execute('DELETE FROM nicks WHERE addr=?', (addr,))
                text = _('** Nick: {}').format(addr)
            elif not nick_re.match(new_nick):
                text = _(
                    '** Invalid nick, only letters and numbers are allowed, and nick should be less than 30 characters')
            elif cls.db.execute('SELECT * FROM nicks WHERE nick=?', (new_nick,)).fetchone():
                text = _('** Nick already taken')
            else:
                text = _('** Nick: {}').format(new_nick)
                cls.db.execute(
                    'INSERT OR REPLACE INTO nicks VALUES (?,?)', (addr, new_nick))
        else:
            text = _('** Nick: {}').format(cls.get_nick(addr))
        chat.send_text(text)

    @classmethod
    def members_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        r = cls.db.execute(
            'SELECT channel from cchats WHERE id=?', (chat.id,)).fetchone()
        if not r:
            chat.send_text(_('This is not an XMPP channel'))
            return

        me = cls.bot.get_contact()
        text = _('Group Members:\n\n')

        for g in cls.get_cchats(r[0]):
            for c in g.get_contacts():
                if c != me:
                    text += '• {}[dc]\n'.format(
                        cls.get_nick(c.addr))

        for u in cls.xmpp['xep_0045'].get_roster(r[0]):
            if u and u != cls.xmpp.nick:
                text += '• {}[xmpp]\n'.format(u)

        chat.send_text(text)

    @classmethod
    def remove_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        r = cls.db.execute(
            'SELECT channel from cchats WHERE id=?', (chat.id,)).fetchone()
        if not r:
            chat.send_text(_('This is not an XMPP channel'))
            return

        channel = r[0]
        sender = ctx.msg.get_sender_contact().addr
        if not ctx.text:
            ctx.text = sender
        if '@' not in ctx.text:
            r = cls.db.execute(
                'SELECT addr FROM nicks WHERE nick=?', (ctx.text,)).fetchone()
            if not r:
                chat.send_text(_('Unknow user: {}').format(ctx.text))
                return
            ctx.text = r[0]

        for g in cls.get_cchats(channel):
            for c in g.get_contacts():
                if c.addr == ctx.text:
                    g.remove_contact(c)
                    s_nick = cls.get_nick(sender)
                    nick = cls.get_nick(c.addr)
                    text = _('** {} removed by {}').format(nick, s_nick)
                    for g in cls.get_cchats(channel):
                        g.send_text(text)
                    text = _('Removed from {} by {}').format(channel, s_nick)
                    cls.bot.get_chat(c).send_text(text)
                    return

    @classmethod
    def join_cmd(cls, ctx):
        sender = ctx.msg.get_sender_contact()
        if not ctx.text:
            return
        ch = cls.db.execute(
            'SELECT * FROM channels WHERE jid=?', (ctx.text,)).fetchone()
        if ch:
            chats = cls.get_cchats(ch['jid'])
        else:
            cls.xmpp.join_muc(ctx.text)
            cls.db.execute('INSERT INTO channels VALUES (?)', (ctx.text,))
            ch = {'jid': ctx.text}
            chats = []

        for g in chats:
            if sender in g.get_contacts():
                g.send_text(
                    _('You are already a member of this group'))
                return

        g = cls.bot.create_group('🇽 '+ch['jid'], [sender])
        cls.db.execute('INSERT INTO cchats VALUES (?,?)',
                       (g.id, ch['jid']))

        def callback(fut):
            try:
                vcard = fut.result()
                avatar = vcard['vcard_temp']['PHOTO']
                filetype = FTYPES.get(avatar['TYPE'], 'png')
                filename = cls.bot.get_blobpath(
                    'xmpp-avatar.{}'.format(filetype))
                with open(filename, 'wb') as img:
                    img.write(avatar['BINVAL'])
                g.set_profile_image(filename)
            except IqError as e:
                logging.exception(e)
            finally:
                done.set()

        done = Event()
        cls.xmpp['xep_0054'].get_vcard(
            ch['jid'], cached=True, timeout=5).add_done_callback(callback)
        done.wait()

        nick = cls.get_nick(sender.addr)
        text = _('** You joined {} as {}').format(ch['jid'], nick)
        g.send_text(text)


class XMPP(ClientXMPP):

    def __init__(self, bridge):
        ClientXMPP.__init__(self, bridge.cfg['jid'], bridge.cfg['password'])

        self.bridge = bridge
        self.nick = bridge.cfg['nick']
        self.get_args = bridge.bot.get_args
        self.connected = Event()

        self.add_event_handler("session_start", self.session_start)
        self.add_event_handler("message", self.message)

        self.register_plugin('xep_0045')  # Multi-User Chat
        self.register_plugin('xep_0054')  # vcard-temp
        self.register_plugin('xep_0363')  # HTTP File Upload
        self.register_plugin('xep_0128')  # Service Discovery Extensions
        # self.register_plugin('xep_0071')  # XHTML-IM

    def join_muc(self, jid):
        self['xep_0045'].join_muc(jid, self.nick)

    def session_start(self, event):
        self.send_presence(
            pstatus='https://github.com/adbenitez/simplebot')
        self.get_roster()

        for jid in self.bridge.get_channels():
            self.join_muc(jid)

        self.connected.set()

    def message(self, msg):
        if msg['mucnick'] == self.nick:
            return

        args = self.get_args('!join', msg['body'])
        if args is not None:
            self.join_muc(msg['body'][6:])
            return

        args = self.get_args('!members', msg['body'])
        if args is not None:
            me = self.bridge.bot.get_contact()
            text = _('Delta Chat members:\n\n')
            for g in self.bridge.get_cchats(msg['from'].bare):
                for c in g.get_contacts():
                    if c != me:
                        text += '• {}[dc]\n'.format(
                            self.bridge.get_nick(c.addr))
            msg.reply(text).send()
            return

        args = self.get_args('!help', msg['body'])
        if args is not None:
            t = '\n\n'.join(['I am SimpleBot a DeltaChat <--> XMPP bridge',
                             '!join <channel>  to add me to that xmpp channel.',
                             '!members show DC member list'
                             '!help  show this message.',
                             'Source code: https://github.com/adbenitez/simplebot'])
            msg.reply(t).send()
            return

        args = self.get_args('!keys', msg['body'])
        if args is not None:
            text = '\n'.join('{}: {}'.format(
                k, msg[k]) for k in msg.keys())
            msg.reply("RECEIVED:\n\n%s" % text).send()
            return

        if msg['type'] == 'groupchat':
            self.bridge.xmpp2dc(msg)
        elif msg['type'] in ('chat', 'normal'):
            msg.reply('Send !help to learn how to use me').send()


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS channels 
                (jid TEXT,
                PRIMARY KEY(jid))''')
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS cchats 
                (id INTEGER,
                channel TEXT NOT NULL,
                PRIMARY KEY(id))''')
            self.execute(
                '''CREATE TABLE IF NOT EXISTS nicks
                (addr TEXT PRIMARY KEY,
                nick TEXT NOT NULL)''')

    def execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def close(self):
        self.db.close()
