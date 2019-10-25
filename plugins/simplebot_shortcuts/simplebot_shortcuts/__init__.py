# -*- coding: utf-8 -*-
import gettext
import os
import re
import sqlite3

from simplebot import Plugin, PluginFilter, PluginCommand


def rmprefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]


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

        db_path = os.path.join(cls.bot.get_dir(__name__), 'shortcuts.db')
        cls.db = sqlite3.connect(db_path)
        with cls.db:
            cls.db.execute(
                '''CREATE TABLE IF NOT EXISTS shortcuts 
                       (addr TEXT NOT NULL,
                        shortcut TEXT NOT NULL,
                        cmd TEXT NOT NULL,
                        PRIMARY KEY(addr, shortcut))''')

        cls.description = _('Allows to create custom shortcuts for commands.')
        cls.long_description = _('')
        cls.filters = [PluginFilter(cls.process_shortcuts)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand('/shortcut', ['"<shortcut>"', '"<cmd>"'],
                          _('Create a shortcut for the given command, if the shortcut ends with {}, then in the associated command, {} will be replaced with the arguments passed to the shortcut, for example: /shortcut "say hello to {}" "/echo hello {}!!!"'), cls.shortcut_cmd),
            PluginCommand('/shortcut/del', ['<shortcut>'],
                          _('Delete a shortcut you had created'), cls.del_cmd),
            PluginCommand('/shortcut/list', [],
                          _('List your shortcuts'), cls.list_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def shortcut_cmd(cls, ctx):
        m = cls.regex.match(ctx.text)
        chat = cls.bot.get_chat(ctx.msg)
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
                               (ctx.msg.get_sender_contact().addr, shortcut, cmd))
            chat.send_text(_('Shortcut created'))
        else:
            chat.send_text(_('Invalid syntax'))

    @classmethod
    def del_cmd(cls, ctx):
        shortcut = ctx.text.strip()
        addr = ctx.msg.get_sender_contact().addr
        with cls.db:
            cur = cls.db.execute(
                'DELETE FROM shortcuts WHERE addr=? and shortcut=?', (addr, shortcut))
        if cur.rowcount <= 0:
            cls.bot.get_chat(ctx.msg).send_text(_('Unknown shortcut'))

    @classmethod
    def list_cmd(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        shortcuts = cls.db.execute(
            'SELECT shortcut, cmd FROM shortcuts WHERE addr=?', (addr,)).fetchall()
        chat = cls.bot.get_chat(ctx.msg)
        if not shortcuts:
            chat.send_text(_('You have not shortcuts yet'))
        else:
            text = '\n\n'.join('"{}":\n"{}"'.format(*s) for s in shortcuts)
            chat.send_text(text)

    @classmethod
    def process_shortcuts(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr
        shortcut = ctx.text.strip().lower()
        for sc, cmd in cls.db.execute('SELECT shortcut, cmd FROM shortcuts WHERE addr=?', (addr,)):
            if sc.endswith('{}') and shortcut.startswith(sc[:-3]):
                ctx.text = cmd.format(rmprefix(shortcut, sc[:-3]).lstrip())
                cls.bot.on_command(ctx)
                ctx.processed = True
                break
            elif shortcut == sc:
                ctx.text = cmd
                cls.bot.on_command(ctx)
                ctx.processed = True
                break
