# -*- coding: utf-8 -*-
import gettext
import imaplib
import os
import re
import sqlite3

from simplebot import Plugin, PluginCommand
import psutil


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
            PluginCommand('/admin/ban', ['<rule>'],
                          _('Ignore addresses matching the give regular expression'), cls.ban_cmd),
            PluginCommand('/admin/unban', ['<rule>'],
                          _('Remove the given rule'), cls.unban_cmd),
            PluginCommand('/admin/banlist', [],
                          _('Display the list of rules'), cls.banlist_cmd),
            PluginCommand('/admin/rmmsg', ['<id>'],
                          _('Remove the given message or message range from the INBOX'), cls.rmmsg_cmd),
            PluginCommand('/admin/delrss', ['<feed>'],
                          _('Delete the RSS with the give url from the RSS data base (needs simplebot_rss plugin)'), cls.delrss_cmd),
            PluginCommand('/admin/joinchannel', ['<id>'],
                          _('Join a channel as admin (needs simplebot_groupmaster plugin)'), cls.joinchannel_cmd),
            PluginCommand('/admin/stats', [], _('Show statistics about the bot'), cls.stats_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.bot.remove_on_msg_detected_listener(cls.msg_detected)
        cls.bot.remove_on_cmd_detected_listener(cls.msg_detected)
        cls.db.close()

    @classmethod
    def msg_detected(cls, ctx):
        addr = ctx.msg.get_sender_contact().addr

        if addr not in cls.cfg['admins'].split():
            for r in cls.db.execute('SELECT * FROM blacklist'):
                if re.match(r[0], addr):
                    ctx.rejected = True
                    break

    @classmethod
    def ban_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        if ctx.msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        cls.db.insert(ctx.text)
        chat.send_text(_('Rule added: {}').format(ctx.text))

    @classmethod
    def unban_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        if ctx.msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        cls.db.delete(ctx.text)
        chat.send_text(_('Rule removed: {}').format(ctx.text))

    @classmethod
    def banlist_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        if ctx.msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        blacklist = cls.db.execute('SELECT * FROM blacklist')
        if blacklist:
            chat.send_text(_('Rules:\n\n{}').format(
                '\n'.join('* '+r[0] for r in blacklist)))
        else:
            chat.send_text(_('The list is empty'))

    @classmethod
    def stats_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        if ctx.msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        text = _('Bot stats:\n\n')

        groups = 0
        private = 0
        chats = cls.bot.get_chats()
        for c in chats:
            if cls.bot.is_group(c):
                groups += 1
            else:
                private += 1
        contacts = len(cls.bot.account.get_contacts())
        text += _('Groups: {:,}\nPrivate Chats: {:,}\nContacts: {:,}\n\n').format(
            groups, private, contacts)

        # TODO: check server flags
        imap = imaplib.IMAP4_SSL(
            cls.bot.account.get_config('configured_mail_server'))
        user = cls.bot.account.get_config('configured_mail_user')
        password = cls.bot.account.get_config('configured_mail_pw')
        imap.login(user, password)
        r = imap.select()
        if r[0] == 'OK':
            text += _('INBOX: {}\n').format(r[1][0].decode())

        mem = psutil.Process(os.getpid()).memory_info().rss
        disk = get_size(cls.bot.basedir)
        text += _('RAM usage: {:,}\nDisk usage: {:,}\n').format(mem, disk)

        chat.send_text(text)

    @classmethod
    def rmmsg_cmd(cls, ctx):
        # TODO: check server flags
        imap = imaplib.IMAP4_SSL(
            cls.bot.account.get_config('configured_mail_server'))
        user = cls.bot.account.get_config('configured_mail_user')
        password = cls.bot.account.get_config('configured_mail_pw')
        imap.login(user, password)
        r = imap.select()
        if r[0] == 'OK':
            imap.store(ctx.text, '+FLAGS', r'\Deleted')
            imap.expunge()

    @classmethod
    def delrss_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        if ctx.msg.get_sender_contact().addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        from simplebot_rss import RSS
        RSS.db.execute(
            'DELETE FROM feeds WHERE url=?', (ctx.text,))
        chat.send_text('Feed deleted')

    @classmethod
    def joinchannel_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        sender = ctx.msg.get_sender_contact()

        if sender.addr not in cls.cfg['admins'].split():
            chat.send_text(_('You are not an administrator'))
            return

        from simplebot_groupmaster import GroupMaster
        r = GroupMaster.db.execute(
            'SELECT admin FROM channels WHERE id=?', (ctx.text,)).fetchone()
        cls.bot.get_chat(r[0]).add_contact(sender)


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


def get_size(path):
    total_size = 0
    for root, dirs, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                except FileNotFoundError:
                    pass
        for d in dirs.copy():
            if os.path.islink(os.path.join(root, d)):
                dirs.remove(d)
    return total_size
