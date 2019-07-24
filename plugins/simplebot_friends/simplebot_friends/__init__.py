# -*- coding: utf-8 -*-
import gettext
import os
import re
import sqlite3

from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape


class DeltaFriends(Plugin):

    name = 'DeltaFriends'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!friends'

    MAX_BIO_LEN = 250

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.conn = sqlite3.connect(os.path.join(cls.ctx.basedir, 'deltafriends.db'))
        with cls.conn:
            cls.conn.execute('''CREATE TABLE IF NOT EXISTS deltafriends (addr TEXT NOT NULL, bio TEXT, PRIMARY KEY(addr))''')

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_friends', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_friends', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin.description')
        cls.long_description = _('plugin.long_description').format(cls.MAX_BIO_LEN)
        cls.NOSCRIPT = _('noscript_msg')
        cls.JOIN_BTN = _('join_btn')
        cls.LEAVE_BTN = _('leave_btn')
        cls.LIST_BTN = _('list_btn')
        cls.PROFILE_HEADER = _('profile_header')
        cls.BIO = _('bio_label')
        cls.WRITE_BTN = _('write_btn')
    
    @classmethod
    def deactivate(cls, ctx):
        cls.conn.close()

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!friends', msg.text)
        if arg is None:
            return False
        req = arg
        for cmd,action in [('!join', cls.join_cmd), ('!leave', cls.leave_cmd),
                           ('!list', cls.list_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                action(msg, arg)
                break
        else:
            if not req:
                addr = msg.get_sender_contact().addr
                bio = cls.conn.execute('SELECT bio FROM deltafriends WHERE addr=?',(addr,)).fetchone()
                if bio is None:
                    bio = ""
                else:
                    bio = bio[0]
                html = cls.env.get_template('index.html').render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr, bio=bio)
                with open(cls.TEMP_FILE, 'w') as fd:
                    fd.write(html)
                chat = cls.ctx.acc.create_chat_by_message(msg)
                chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True

    @classmethod
    def list_cmd(cls, msg, *args):
        friends = [{'addr':addr, 'bio':bio}
                   for addr,bio in cls.conn.execute('SELECT * FROM deltafriends ORDER BY addr').fetchall()]
        html = cls.env.get_template('list.html').render(plugin=cls, friends=friends)
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')

    @classmethod
    def join_cmd(cls, msg, text):
        addr = msg.get_sender_contact().addr
        text = ' '.join(text.split())
        if len(text) > cls.MAX_BIO_LEN:
            text = text[:cls.MAX_BIO_LEN] + '...'
        with cls.conn:
            cls.conn.execute('INSERT OR REPLACE INTO deltafriends VALUES (?, ?)', (addr, text))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(_('user_added'))

    @classmethod
    def leave_cmd(cls, msg, *args):
        addr = msg.get_sender_contact().addr
        with cls.conn:
            rowcount = cls.conn.execute('DELETE FROM deltafriends WHERE addr=?', (addr,)).rowcount
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if rowcount == 1:
            chat.send_text(_('user_removed'))
        else:
            chat.send_text(_('user_not_found'))
