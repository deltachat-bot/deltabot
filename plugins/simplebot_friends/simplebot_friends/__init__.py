# -*- coding: utf-8 -*-
import gettext
import os
import sqlite3

from simplebot import Plugin, Mode, PluginCommand
from jinja2 import Environment, PackageLoader, select_autoescape


class DeltaFriends(Plugin):

    name = 'DeltaFriends'
    version = '0.4.0'

    MAX_BIO_LEN = 500

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'deltafriends.db'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_friends', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Provides a directory of Delta Chat users.')
        cls.commands = [
            PluginCommand('/friends/join', ['<bio>'],
                          _('Will add you to the list or update your bio, <bio> is up to {0} characters of text describing yourself').format(cls.MAX_BIO_LEN), cls.join_cmd),
            PluginCommand('/friends/leave', [], _('Will remove you from the DeltaFriends list'),
                          cls.leave_cmd),
            PluginCommand('/friends/list', [],
                          _('Will return the list of users wanting to make new friends'), cls.list_cmd),
            PluginCommand('/friends/me', [],
                          _('Sends your biography'), cls.me_cmd),
            PluginCommand('/friends/app', [], _('Sends an html app to help you to use the plugin'), cls.app_cmd)]
        cls.bot.add_commands(cls.commands)

        cls.NOSCRIPT = _(
            'You need a browser with JavaScript support for this page to work correctly.')
        cls.JOIN_BTN = _('Join/Update')
        cls.LEAVE_BTN = _('Leave')
        cls.LIST_BTN = _('Users List')
        cls.PROFILE_HEADER = _('Profile')
        cls.BIO = _('Bio')
        cls.WRITE_BTN = _('Write')

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.db.close()

    @classmethod
    def app_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        row = cls.db.execute(
            'SELECT bio FROM deltafriends WHERE addr=?', (addr,), 'one')
        if row is None:
            bio = ""
        else:
            bio = row['bio']
        html = cls.env.get_template('index.html').render(
            plugin=cls, bot_addr=cls.bot.get_address(), bio=bio)
        chat = cls.bot.get_chat(ctx.msg)
        cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)

    @classmethod
    def list_cmd(cls, ctx):
        friends = cls.db.execute('SELECT * FROM deltafriends ORDER BY addr')
        chat = cls.bot.get_chat(ctx.msg)
        if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
            text = _('{0} ({1}):\n\n').format(cls.name, len(friends))
            for f in friends:
                text += '{0}:\n{1}\n\n'.format(f['addr'], f['bio'])
            chat.send_text(text)
        else:
            html = cls.env.get_template('list.html').render(
                plugin=cls, friends=friends)
            cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)

    @classmethod
    def join_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        text = ' '.join(ctx.text.split())
        if len(text) > cls.MAX_BIO_LEN:
            text = text[:cls.MAX_BIO_LEN] + '...'
        cls.db.execute(
            'INSERT OR REPLACE INTO deltafriends VALUES (?, ?)', (addr, text))
        chat = cls.bot.get_chat(ctx.msg)
        chat.send_text(_('You are now in the DeltaFriends list'))

    @classmethod
    def leave_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        cls.db.execute(
            'DELETE FROM deltafriends WHERE addr=?', (addr,))
        chat = cls.bot.get_chat(ctx.msg)
        chat.send_text(_('You was removed from the DeltaFriends list'))

    @classmethod
    def me_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        row = cls.db.execute(
            'SELECT bio FROM deltafriends WHERE addr=?', (addr,), 'one')
        if row is None:
            bio = _('You have not set a biography')
        else:
            bio = '{}:\n{}'.format(addr, row['bio'])
        cls.bot.get_chat(ctx.msg).send_text(bio)


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.db.execute(
            '''CREATE TABLE IF NOT EXISTS deltafriends 
            (addr TEXT NOT NULL,
            bio TEXT,
            PRIMARY KEY(addr))''')

    def execute(self, statement, args=(), get='all'):
        with self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def close(self):
        self.db.close()
