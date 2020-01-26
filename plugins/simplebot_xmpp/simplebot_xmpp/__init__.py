# -*- coding: utf-8 -*-
from threading import Thread, Event
import gettext
import os
import sqlite3

from simplebot import Plugin, PluginCommand, PluginFilter
from slixmpp import ClientXMPP
from slixmpp.exceptions import IqError, IqTimeout, TimeoutError


import logging
logging.basicConfig(level=logging.DEBUG,
                    format='%(levelname)-8s %(message)s')


def timeout_callback(arg):
    raise TimeoutError("could not send message in time")


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

        print('XMPP - Connecting...')
        cls.xmpp = XMPP(cls)
        cls.xmpp.connect()
        cls.worker = Thread(target=cls.listen_to_xmpp)
        cls.worker.start()
        cls.xmpp.connected.wait()
        print('XMPP - Connected!')

        cls.description = _('A bridge between Delta Chat and XMPP network.')
        cls.filters = [PluginFilter(cls.process_messages)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand(
                '/xmpp/join', ['<jid>'], _('Join to the given XMPP channel'), cls.join_cmd),
            PluginCommand('/xmpp/nick', ['[nick]'],
                          _('Set your nick or display your current nick if no new nick is given'), cls.nick_cmd)
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def get_nick(cls, addr):
        r = cls.db.execute(
            'SELECT nick from nicks WHERE addr=?', (addr,)).fetchone()
        if r:
            return r[0]
        else:
            return addr

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
            text = _('** {}[dc] left the group').format(nick)
            cls.xmpp.send_message(r[0], text, mtype='groupchat')
            for g in cls.get_cchats(r[0]):
                g.send_text(text)
            return

        if ctx.msg.is_text():
            text = '{}[dc]:\n{}'.format(nick, ctx.text)
            cls.xmpp.send_message(r[0], text, mtype='groupchat')
            for g in cls.get_cchats(r[0]):
                if g.id != chat.id:
                    g.send_text(text)
        elif ctx.msg.filename:
            text = '{}[dc]:\n{}'.format(nick, ctx.text)
            cls.xmpp.send_message(r[0], text, mtype='groupchat')
            url = await cls.xmpp['xep_0363'].upload_file(
                ctx.msg.filename, timeout=10, timeout_callback=tcallback)
            html = '<body xmlns="http://www.w3.org/1999/xhtml">{0}<br/><a href="{1}">{1}</a></body>'
            html = html.format(text, url)
            for g in cls.get_cchats(r[0]):
                if g.id != chat.id:
                    g.send_text('{}\n{}'.format(text, url))
        else:
            chat.send_text(_('Unsuported message'))

    @classmethod
    def xmpp2dc(cls, msg):
        for g in cls.get_cchats(msg['mucroom']):
            g.send_text('{0[mucnick]}:\n{0[body]}'.format(msg))

    @classmethod
    def nick_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        addr = ctx.msg.get_sender_contact().addr
        new_nick = ' '.join(ctx.text.split())
        if new_nick:
            if new_nick == addr:
                cls.db.execute('DELETE FROM nicks WHERE addr=?', (addr,))
                text = _('** Nick: {}').format(addr)
            elif '@' in new_nick or ':' in new_nick or len(new_nick) > 30:
                text = _(
                    '** Invalid nick, "@" and ":" not allowed, and nick should be less than 30 characters')
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
    def join_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
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
                chat.send_text(
                    _('You are already a member of that group'))
                return
        g = cls.bot.create_group('🇽 '+ch['jid'], [sender])
        cls.db.execute('INSERT INTO cchats VALUES (?,?)',
                       (g.id, ch['jid']))

        text = _(
            '** {}[dc] joined the group').format(cls.get_nick(sender.addr))
        cls.xmpp.send_message(ch['jid'], text, mtype='groupchat')
        for c in chats:
            c.send_text(text)
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
        self.register_plugin('xep_0363')  # HTTP File Upload

    def join_muc(self, jid):
        self.plugin['xep_0045'].join_muc(jid, self.nick)

    def session_start(self, event):
        self.send_presence(
            pstatus='https://github.com/adbenitez/simplebot')
        self.get_roster()

        for jid in self.bridge.get_channels():
            print('JOINING: ', jid)
            self.join_muc(jid)

        self.connected.set()

    def message(self, msg):
        if msg['mucnick'] == self.nick:
            return

        args = self.get_args('/join', msg['body'])
        if args is not None:
            self.join_muc(msg['body'][6:])
            return

        args = self.get_args('/help', msg['body'])
        if args is not None:
            msg.reply('I am SimpleBot a DeltaChat <--> XMPP bridge\n/join <channel> to add me to that xmpp channel.\n/help show this message.\nSource code: https://github.com/adbenitez/simplebot').send()
            return

        args = self.get_args('/keys', msg['body'])
        if args is not None:
            text = '\n'.join('{}: {}'.format(
                k, msg[k]) for k in msg.keys())
            msg.reply("RECEIVED:\n\n%s" % text).send()
            return

        if msg['type'] == 'groupchat':
            self.bridge.xmpp2dc(msg)
        elif msg['type'] in ('chat', 'normal'):
            msg.reply('Send /help to learn how to use me').send()


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
