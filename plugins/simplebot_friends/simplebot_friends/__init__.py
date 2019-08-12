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

    MAX_BIO_LEN = 250

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        cls.TEMP_FILE = os.path.join(cls.bot.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.conn = sqlite3.connect(os.path.join(
            cls.bot.basedir, 'deltafriends.db'))
        with cls.conn:
            cls.conn.execute(
                '''CREATE TABLE IF NOT EXISTS deltafriends (addr TEXT NOT NULL, bio TEXT, PRIMARY KEY(addr))''')

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_friends', localedir=localedir,
                                       languages=[bot.locale])
        except OSError:
            lang = gettext.translation('simplebot_friends', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('Provides a directory of Delta Chat users.')
        cls.commands = [
            ('/friends/join', ['<bio>'],
             _('Will add you to the list or update your bio, <bio> is up to {} characters of text describing yourself.').format(
                 cls.MAX_BIO_LEN),
             cls.join_cmd),
            ('/friends/leave', [], _('Will remove you from the DeltaFriends list.'),
             cls.leave_cmd),
            ('/friends/list', [],
             _('Will return the list of users wanting to make new friends.'), cls.list_cmd),
            ('/friends/html', [], _('Sends an html app to help you to use the plugin.'), cls.html_cmd)]
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
    def deactivate(cls, bot):
        cls.conn.close()

    @classmethod
    def html_cmd(cls, msg, text):
        addr = msg.get_sender_contact().addr
        bio = cls.conn.execute(
            'SELECT bio FROM deltafriends WHERE addr=?', (addr,)).fetchone()
        if bio is None:
            bio = ""
        else:
            bio = bio[0]
        html = cls.env.get_template('index.html').render(
            plugin=cls, bot_addr=cls.bot.get_address(), bio=bio)
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.bot.get_chat(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')

    @classmethod
    def list_cmd(cls, msg, *args):
        friends = [{'addr': addr, 'bio': bio}
                   for addr, bio in cls.conn.execute('SELECT * FROM deltafriends ORDER BY addr').fetchall()]
        html = cls.env.get_template('list.html').render(
            plugin=cls, friends=friends)
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.bot.get_chat(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')

    @classmethod
    def join_cmd(cls, msg, text):
        addr = msg.get_sender_contact().addr
        text = ' '.join(text.split())
        if len(text) > cls.MAX_BIO_LEN:
            text = text[:cls.MAX_BIO_LEN] + '...'
        with cls.conn:
            cls.conn.execute(
                'INSERT OR REPLACE INTO deltafriends VALUES (?, ?)', (addr, text))
        chat = cls.bot.get_chat(msg)
        chat.send_text(_('You are now in the DeltaFriends list'))

    @classmethod
    def leave_cmd(cls, msg, *args):
        addr = msg.get_sender_contact().addr
        with cls.conn:
            rowcount = cls.conn.execute(
                'DELETE FROM deltafriends WHERE addr=?', (addr,)).rowcount
        chat = cls.bot.get_chat(msg)
        if rowcount == 1:
            chat.send_text(_('You was removed from the DeltaFriends list'))
        else:
            chat.send_text(_('You are NOT in the DeltaFriends list'))
