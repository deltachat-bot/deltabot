# -*- coding: utf-8 -*-
import gettext
import os
import re
import sqlite3

from simplebot import Plugin


class Admin(Plugin):

    name = 'Admin'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.cfg = cls.bot.get_config(__name__)
        if cls.cfg.get('admins') is None:
            cls.cfg['admins'] = ''
            cls.bot.save_config()

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_admin', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.db = DBManager(
            os.path.join(cls.bot.get_dir(__name__), 'admin.db'))

        cls.description = _('Administration tools for bot operators.')
        cls.long_description = _(
            'If you are an user just ignore this plugin, only bot administrators can use this functionality.')

        cls.bot.add_on_msg_detected_listener(cls.msg_detected)
        cls.bot.add_on_cmd_detected_listener(cls.msg_detected)
        cls.commands = [
            ('/admin/ban', ['<rule>'],
             _('Ignore addresses matching the give regular expression'), cls.ban_cmd),
            ('/admin/unban', ['<rule>'],
             _('Remove the given rule'), cls.unban_cmd),
            ('/admin/banlist', [],
             _('Display the list of rules'), cls.banlist_cmd),
            ('/admin/stats', [], _('Show statistics about the bot'), cls.stats_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.bot.remove_on_msg_detected_listener(cls.msg_detected)
        cls.bot.remove_on_cmd_detected_listener(cls.msg_detected)
        cls.db.close()

    @classmethod
    def msg_detected(cls, msg, text):
        addr = msg.get_sender_contact().addr

        if addr not in cls.cfg['admins'].split():
            for r in cls.db.execute('SELECT * FROM blacklist'):
                if re.match(r[0], addr):
                    return None
        return text

    @classmethod
    def ban_cmd(cls, msg, rule):
        chat = cls.bot.get_chat(msg)

        if msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        cls.db.insert(rule)
        chat.send_text(_('Rule added: {}').format(rule))

    @classmethod
    def unban_cmd(cls, msg, rule):
        chat = cls.bot.get_chat(msg)

        if msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        cls.db.delete(rule)
        chat.send_text(_('Rule removed: {}').format(rule))

    @classmethod
    def banlist_cmd(cls, msg, args):
        chat = cls.bot.get_chat(msg)

        if msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        blacklist = cls.db.execute('SELECT * FROM blacklist')
        if blacklist:
            chat.send_text(_('Rules:\n\n{}').format(
                '\n'.join('* '+r[0] for r in blacklist)))
        else:
            chat.send_text(_('The list is empty'))

    @classmethod
    def stats_cmd(cls, msg, args):
        chat = cls.bot.get_chat(msg)

        if msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        groups = 0
        private = 0
        messages = 0
        chats = cls.bot.get_chats()
        for c in chats:
            if cls.bot.is_group(c):
                groups += 1
            else:
                private += 1
            messages += len(c.get_messages())
        contacts = len(cls.bot.account.get_contacts())
        # TODO: get basedir size
        chat.send_text(_('Bot stats:\n\nGroups: {}\nPrivate Chats: {}\nContacts: {}\nMessages: {}').format(
            groups, private, contacts, messages))


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.execute(
            '''CREATE TABLE IF NOT EXISTS blacklist
            (addr TEXT NOT NULL,
            PRIMARY KEY(addr))''')

    def execute(self, statement, args=(), get='all'):
        with self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def insert(self, addr):
        self.execute('INSERT INTO blacklist VALUES (?)', (addr,))

    def delete(self, addr):
        self.execute('DELETE FROM blacklist WHERE addr=?', (addr,))

    def close(self):
        self.db.close()
