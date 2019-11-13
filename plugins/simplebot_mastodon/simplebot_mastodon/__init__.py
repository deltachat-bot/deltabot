# -*- coding: utf-8 -*-
from enum import IntEnum
import gettext
import os
import sqlite3

from simplebot import Plugin, PluginCommand, PluginFilter
from mastodon import Mastodon


class Status(IntEnum):
    DISABLED = 0
    ENABLED = 1


class MastodonBridge(Plugin):

    name = 'Mastodon Bridge'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_mastodon', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'mastodon.db'))

        cls.description = _(
            'A bridge between Delta Chat and Mastodon network.')
        cls.filters = [PluginFilter(cls.process_messages)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand('/masto/login', ['<instance>', '<user>', '<pass>'],
                          _('Login in Mastodon'), cls.login_cmd),
            PluginCommand('/masto/logout', ['[instance]', '[user]'],
                          _('Logout from Mastodon'), cls.logout_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.db.close()

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        account = cls.db.execute(
            'SELECT * FROM users WHERE toots=?', (chat.id,)).fetchone()
        if account:
            ctx.processed = True
            if account['status'] == Status.DISABLED:
                chat.send_text(
                    _('Your account is disabled, use /masto/enable to enable it.'))
            elif ctx.text:
                m = cls.get_session(account)
                m.toot(ctx.text)

    @classmethod
    def login_cmd(cls, ctx):
        api_url, uname, passwd = ctx.text.split(maxsplit=2)
        chat = cls.bot.get_chat(ctx.msg)

        old_user = cls.db.execute(
            'SELECT * FROM users WHERE username=? AND api_url=?', (uname, api_url)).fetchone()
        if old_user:
            chat.send_text(_('Account already in use'))
        else:
            addr = ctx.msg.get_sender_contact().addr
            m = Mastodon(api_base_url=api_url, ratelimit_method='throw')
            access_token = m.log_in(uname, passwd)
            tgroup = cls.bot.create_group(
                '[M] Toot to {}'.format(api_url), [addr])
            sgroup = cls.bot.create_group(
                '[M] Setting ({})'.format(api_url), [addr])
            cls.db.insert_user(
                (api_url, uname, access_token, addr, Status.ENABLED, tgroup.id, sgroup.id))
            tgroup.send_text(
                _('Messages you send here will be tooted to {}\nAccount: {}').format(api_url, uname))
            sgroup.send_text(
                _('Here you can send commands for {}\nAccount: {}').format(api_url, uname))

    @classmethod
    def logout_cmd(cls, ctx):
        contact = ctx.msg.get_sender_contact()
        addr = contact.addr
        if ctx.text:
            api_url, uname = ctx.text.split(maxsplit=1)
            account = cls.db.execute(
                'SELECT * FROM users WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        else:
            account = cls.db.execute(
                'SELECT * FROM users WHERE settings=?', (chat.id,)).fetchone()

        if account:
            cls.db.delete_user(account)
            me = cls.bot.get_contact()
            cls.get_chat(account['toots']).remove_contact(me)
            cls.get_chat(account['settings']).remove_contact(me)
            cls.bot.get_chat(contact).send_text(_('You have logged out'))
        else:
            cls.bot.get_chat(ctx.msg).send_text(_('Unknow account'))

    @classmethod
    def get_session(cls, account):
        return Mastodon(access_token=account['access_token'], api_base_url=account['api_url'], ratelimit_method='throw')


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS users 
                (api_url TEXT,
                username TEXT,
                access_token TEXT NOT NULL,
                addr TEXT NOT NULL,
                status INTEGER NOT NULL,
                toots INTEGER NOT NULL,
                settings INTEGER NOT NULL,
                PRIMARY KEY(api_url, username))''')

    def execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def insert_user(self, user):
        self.execute(
            'INSERT OR REPLACE INTO users VALUES (?,?,?,?,?,?,?)', user)

    def delete_user(self, account):
        self.execute(
            'DELETE FROM users WHERE api_url=? AND username=?', (account['api_url'], account['username']))

    def close(self):
        self.db.close()
