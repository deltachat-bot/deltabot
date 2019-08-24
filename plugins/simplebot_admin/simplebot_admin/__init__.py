# -*- coding: utf-8 -*-
import gettext
import os
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

        db_path = os.path.join(cls.bot.get_dir(__name__), 'admin.db')
        cls.db = sqlite3.connect(db_path)
        with cls.db:
            cls.db.execute(
                '''CREATE TABLE IF NOT EXISTS blacklist
                       (addr TEXT NOT NULL,
                        PRIMARY KEY(addr))''')

        cls.description = _('Administration tools for bot operators.')
        cls.long_description = _(
            'If you are an user just ignore this plugin, only bot administrators can use this functionality.')

        cls.bot.add_on_msg_detected_listener(cls.msg_detected)
        cls.bot.add_on_cmd_detected_listener(cls.msg_detected)
        cls.commands = [
            ('/admin/ban', ['<addr>'],
             _('The given email address will be ignored by the bot'), cls.ban_cmd),
            ('/admin/unban', ['<addr>'],
             _('The given address will be allowed to use the bot again'), cls.unban_cmd),
            ('/admin/banlist', [],
             _('Display a list of banned addresses'), cls.banlist_cmd),
            ('/admin/stats', [], _('Show statistics about the bot'), cls.stats_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.bot.remove_on_msg_detected_listener(cls.msg_detected)
        cls.bot.remove_on_cmd_detected_listener(cls.msg_detected)

    @classmethod
    def msg_detected(cls, msg, text):
        addr = msg.get_sender_contact().addr
        banned = cls.db.execute(
            'SELECT * FROM blacklist WHERE addr=?', (addr,)).fetchone()
        if banned is None:
            return text
        else:
            return None

    @classmethod
    def ban_cmd(cls, msg, addr):
        chat = cls.bot.get_chat(msg)
        admins = cls.cfg['admins'].split()
        if msg.get_sender_contact().addr not in admins:
            chat.send_text(_('You are not an administrator'))
            return

        if addr in admins:
            chat.send_text(
                _('You can NOT block administrators'))
        else:
            cls._insert(addr)
            chat.send_text(_('{} banned').format(addr))

    @classmethod
    def unban_cmd(cls, msg, addr):
        chat = cls.bot.get_chat(msg)
        if msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        cls._delete(addr)
        chat.send_text(_('{} unblocked').format(addr))

    @classmethod
    def banlist_cmd(cls, msg, args):
        chat = cls.bot.get_chat(msg)
        if msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        blacklist = cls.db.execute('SELECT addr FROM blacklist').fetchall()
        if blacklist:
            chat.send_text(_('Banned addresses:\n\n{}').format(
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

    @classmethod
    def _insert(cls, addr):
        with cls.db:
            cls.db.execute(
                'INSERT INTO blacklist VALUES (?)', (addr,))

    @classmethod
    def _delete(cls, addr):
        with cls.db:
            cls.db.execute(
                'DELETE FROM blacklist WHERE addr=?', (addr,))
