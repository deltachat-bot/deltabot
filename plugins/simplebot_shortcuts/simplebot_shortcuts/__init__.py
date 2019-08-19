# -*- coding: utf-8 -*-
import gettext
import os
import re
import sqlite3

from simplebot import Plugin


class Shortcuts(Plugin):

    name = 'Shortcuts'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.regex = re.compile(
            r'"(?P<shortcut>\S.*?)"\s*"(?P<cmd>\S.*?)"$', re.DOTALL)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_shortcuts', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        db_path = os.path.join(cls.bot.basedir, 'shortcuts.db')
        cls.db = sqlite3.connect(db_path)
        with cls.db:
            cls.db.execute(
                '''CREATE TABLE IF NOT EXISTS shortcuts 
                       (addr TEXT NOT NULL,
                        shortcut TEXT NOT NULL,
                        cmd TEXT NOT NULL,
                        PRIMARY KEY(addr, shortcut))''')

        cls.description = _('Allows to create custom shortcuts for commands.')
        cls.filters = [cls.process_shortcuts]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            ('/shortcut', ['"<shortcut>"', '"<cmd>"'],
             _('Create a shortcut for the given command'), cls.shortcut_cmd),
            ('/shortcut/del', ['<shortcut>'],
             _('Delete a shortcut you had created'), cls.del_cmd),
            ('/shortcut/list', [], _('List your shortcuts'), cls.list_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def shortcut_cmd(cls, msg, args):
        m = cls.regex.match(args)
        chat = cls.bot.get_chat(msg)
        if m is not None:
            shortcut = m.group('shortcut').strip().lower()
            if shortcut.startswith('/'):
                chat.send_text(
                    _('Shortcuts can NOT start with command prefix'))
                return
            cmd = m.group('cmd').strip()
            if not cmd.startswith('/'):
                chat.send_text(_('Command MUST start with the command prefix'))
                return
            with cls.db:
                cls.db.execute('INSERT OR REPLACE INTO shortcuts VALUES (?,?,?)',
                               (msg.get_sender_contact().addr, shortcut, cmd))
            chat.send_text(_('Shortcut created'))
        else:
            chat.send_text(_('Invalid syntax'))

    @classmethod
    def del_cmd(cls, msg, shortcut):
        shortcut = shortcut.strip('"').strip()
        addr = msg.get_sender_contact().addr
        with cls.db:
            deleted = cls.db.execute(
                'DELETE FROM shortcuts WHERE addr=? and shortcut=?', (addr, shortcut)).fetchone()
        if deleted is None:
            cls.bot.get_chat(msg).send_text(_('Unknown shortcut'))

    @classmethod
    def list_cmd(cls, msg, args):
        addr = msg.get_sender_contact().addr
        shortcuts = cls.db.execute(
            'SELECT shortcut, cmd FROM shortcuts WHERE addr=?', (addr,)).fetchall()
        chat = cls.bot.get_chat(msg)
        if not shortcuts:
            chat.send_text(_('You have not shortcuts yet'))
        else:
            text = '\n\n'.join('"{}":\n"{}"'.format(*s) for s in shortcuts)
            chat.send_text(text)

    @classmethod
    def process_shortcuts(cls, msg, text):
        addr = msg.get_sender_contact().addr
        shortcut = text.strip()
        cmd = cls.db.execute(
            'SELECT cmd FROM shortcuts WHERE addr=? and shortcut=?', (addr, shortcut)).fetchone()
        if cmd is None:
            return False
        else:
            cls.bot.on_command(msg, cmd[0])
            return True
