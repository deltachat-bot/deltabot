# -*- coding: utf-8 -*-
from enum import IntEnum, Enum
from threading import Thread, Event
import gettext
import os
import sqlite3

from simplebot import Plugin, PluginCommand, PluginFilter, Mode
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader
import mastodon
import requests


MASTODON_LOGO = os.path.join(os.path.dirname(__file__), 'mastodon-logo.png')


class Status(IntEnum):
    DISABLED = 0
    ENABLED = 1


class Visibility(str, Enum):
    DIRECT = 'direct'  # post will be visible only to mentioned users
    PRIVATE = 'private'  # post will be visible only to followers
    UNLISTED = 'unlisted'  # post will be public but not appear on the public timeline
    PUBLIC = 'public'  # post will be public


class MastodonBridge(Plugin):

    name = 'Mastodon Bridge'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        save = False
        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('delay'):
            cls.cfg['delay'] = '10'
            save = True
        if save:
            cls.bot.save_config()

        cls.env = Environment(loader=PackageLoader(__name__, 'templates'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_mastodon', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.REPLY_BTN = _('Reply')

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'mastodon.db'))

        cls.worker = Thread(target=cls.listen_to_mastodon)
        cls.worker.deactivated = Event()
        cls.worker.start()

        cls.description = _(
            'A bridge between Delta Chat and Mastodon network.')
        cls.filters = [PluginFilter(cls.process_messages)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand('/masto/login', ['<instance>', '<email>', '<pass>'],
                          _('Login in Mastodon'), cls.login_cmd),
            PluginCommand('/masto/logout', ['[instance]', '[user]'],
                          _('Logout from Mastodon'), cls.logout_cmd),
            PluginCommand('/masto/direct', ['<user>'],
                          _('Start a private chat with the given Mastodon user'), cls.direct_cmd),
            PluginCommand('/masto/reply', ['<instance>', '<user>', '<id>'],
                          _('Reply to a toot with the given id'), cls.reply_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.db.close()

    @classmethod
    def get_session(cls, acc):
        return Mastodon(access_token=acc['access_token'], api_base_url=acc['api_url'], ratelimit_method='throw')

    @classmethod
    def toot(cls, ctx, acc, visibility=None, in_reply_to=None):
        m = cls.get_session(acc)
        if ctx.msg.is_image() or ctx.msg.is_gif() or ctx.msg.is_video() or ctx.msg.is_audio():
            media = m.media_post(ctx.msg.filename)
            if in_reply_to:
                m.status_reply(in_reply_to, ctx.text,
                               media_ids=media, visibility=visibility)
            else:
                m.status_post(ctx.text, media_ids=media, visibility=visibility)
        elif ctx.text:
            if in_reply_to:
                m.status_reply(in_reply_to, ctx.text, visibility=visibility)
            else:
                m.status_post(ctx.text, visibility=visibility)
        else:
            cls.bot.get_chat(ctx.msg).send_text(_('Unsuported message type'))

    @classmethod
    def delete_account(cls, acc):
        me = cls.bot.get_contact()
        for pv in cls.db.execute('SELECT * FROM priv_chats WHERE api_url=? AND username=?', (acc['api_url'], acc['username'])):
            cls.bot.get_chat(pv['id']).remove_contact(me)
        cls.bot.get_chat(acc['toots']).remove_contact(me)
        cls.bot.get_chat(acc['notifications']).remove_contact(me)
        cls.bot.get_chat(acc['settings']).remove_contact(me)
        cls.db.delete_account(acc)

    @classmethod
    def listen_to_mastodon(cls):
        while True:
            if cls.worker.deactivated.is_set():
                return
            cls.bot.logger.debug('Checking Mastodon')
            for acc in cls.db.execute('SELECT * FROM accounts WHERE status=?', (Status.ENABLED,)):
                if cls.worker.deactivated.is_set():
                    return
                try:
                    m = cls.get_session(acc)
                    max_id = None
                    dmsgs = []
                    mentions = []
                    while True:
                        ment = m.mentions(
                            max_id=max_id, since_id=acc['last_notification'])
                        if not ment:
                            break
                        if max_id is None:
                            cls.db.execute('UPDATE accounts SET last_notification=? WHERE api_url=? AND username=?', (
                                ment[0]['id'], acc['api_url'], acc['username']))
                        max_id = ment[-1]
                        for mention in ment:
                            if not mention['type'] == 'mention':
                                continue
                            s = mention['status']
                            if s['visibility'] == Visibility.DIRECT and len(s['mentions']) == 1:
                                dmsgs.append(s)
                            else:
                                mentions.append(s)
                    for dm in reversed(dmsgs):
                        acct = dm['account']['acct'].lower()
                        text = '{} (@{}):\n\n'.format(
                            dm['account']['display_name'], acct)

                        media_urls = '\n'.join(
                            media['url'] for media in dm['media_attachments'])
                        if media_urls:
                            text += media_urls + '\n\n'

                        soup = BeautifulSoup(dm['content'], 'html.parser')
                        accts = {e['url']: '@'+e['acct']
                                 for e in dm['mentions']}
                        for a in soup('a', class_='mention'):
                            a.string = accts.get(a['href'], a.string)
                        for br in soup('br'):
                            br.replace_with('\n')
                        for p in soup('p'):
                            p.replace_with(p.get_text()+'\n\n')
                        text += soup.get_text()

                        pv = cls.db.execute(
                            'SELECT * FROM priv_chats WHERE api_url=? AND username=? AND contact=?', (acc['api_url'], acc['username'], acct)).fetchone()
                        if pv:
                            g = cls.bot.get_chat(pv['id'])
                            if g is None:
                                cls.db.execute(
                                    'DELETE FROM priv_chats WHERE id=?', (pv['id'],))
                            else:
                                g.send_text(text)
                        else:
                            g = cls.bot.create_group(
                                '🇲 {} ({})'.format(acct, acc['api_url']), [acc['addr']])
                            cls.db.execute(
                                'INSERT INTO priv_chats VALUES (?,?,?,?)', (g.id, acct, acc['api_url'], acc['username']))

                            file_name = cls.bot.get_blobpath(
                                'mastodon-avatar.jpg')
                            r = requests.get(dm['account']['avatar_static'])
                            with open(file_name, 'wb') as fd:
                                fd.write(r.content)

                            g.send_text(text)
                            g.set_profile_image(file_name)

                    chat = cls.bot.get_chat(acc['notifications'])
                    pref = cls.bot.get_preferences(acc['addr'])
                    if pref['mode'] in (Mode.TEXT, Mode.TEXT_HTMLZIP):
                        for mention in reversed(mentions):
                            text = '{} (@{}):\n\n'.format(
                                mention.account.display_name, mention.account.acct)

                            media_urls = '\n'.join(
                                media.url for media in mention.media_attachments)
                            if media_urls:
                                text += media_urls + '\n\n'

                            soup = BeautifulSoup(
                                mention.content, 'html.parser')
                            accts = {e.url: '@'+e.acct
                                     for e in mention.mentions}
                            for a in soup('a', class_='mention'):
                                a.string = accts.get(a['href'], a.string)
                            for br in soup('br'):
                                br.replace_with('\n')
                            for p in soup('p'):
                                p.replace_with(p.get_text()+'\n\n')
                            text += soup.get_text()

                            text += '\n\n[{}]'.format(mention.visibility)

                            chat.send_text(text)
                    else:
                        me = cls.bot.get_contact().addr
                        html = cls.env.get_template('items.html').render(
                            plugin=cls, mentions=mentions, bot_addr=me, api_url=acc['api_url'], username=acc['username'])
                        cls.bot.send_html(chat, html, cls.name, pref['mode'])
                except Exception as ex:
                    cls.bot.logger.exception(ex)
            cls.worker.deactivated.wait(cls.cfg.getint('delay'))

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        account = cls.db.execute(
            'SELECT * FROM accounts WHERE toots=?', (chat.id,)).fetchone()
        if account:
            ctx.processed = True
            if account['status'] == Status.DISABLED:
                cls.db.execute('UPDATE accounts SET status=? WHERE api_url=? AND username=?', (
                    Status.ENABLED, account['api_url'], account['username']))
            cls.toot(ctx, account)
            return

        pv = cls.db.execute(
            'SELECT * FROM priv_chats WHERE id=?', (chat.id,)).fetchone()
        if pv:
            ctx.processed = True
            if len(chat.get_contacts()) == 1:
                cls.db.execute('DELETE FROM priv_chats WHERE id=?', (chat.id,))
            else:
                ctx.text = '@{} {}'.format(pv['contact'], ctx.text)
                account = cls.db.execute(
                    'SELECT * FROM accounts WHERE api_url=? AND username=?', (pv['api_url'], pv['username'])).fetchone()
                cls.toot(ctx, account, visibility=Visibility.DIRECT)
            return

        account = cls.db.execute(
            'SELECT * FROM accounts WHERE settings=?', (chat.id,)).fetchone()
        if account:
            ctx.processed = True
            if len(chat.get_contacts()) == 1:
                cls.delete_account(account)

    @classmethod
    def login_cmd(cls, ctx):
        api_url, email, passwd = ctx.text.split(maxsplit=2)
        chat = cls.bot.get_chat(ctx.msg)

        m = Mastodon(api_base_url=api_url, ratelimit_method='throw')
        access_token = m.log_in(email, passwd)
        uname = m.me()['acct'].lower()

        old_user = cls.db.execute(
            'SELECT * FROM accounts WHERE username=? AND api_url=?', (uname, api_url)).fetchone()
        if old_user:
            chat.send_text(_('Account already in use'))
        else:
            n = m.notifications(limit=1)
            last_notification = n[0]['id'] if n else None

            addr = ctx.msg.get_sender_contact().addr
            tgroup = cls.bot.create_group(
                'Toot to {}'.format(api_url), [addr])
            ngroup = cls.bot.create_group(
                'Notifications ({})'.format(api_url), [addr])
            sgroup = cls.bot.create_group(
                'Settings ({})'.format(api_url), [addr])

            cls.db.insert_user(
                (api_url, uname, access_token, addr, Status.ENABLED, tgroup.id, ngroup.id, sgroup.id, last_notification))

            sgroup.send_text(
                _('Here you can send commands for account: {} at {}\n\nTo logout from the bridge just leave this group').format(uname, api_url))
            sgroup.set_profile_image(MASTODON_LOGO)
            tgroup.send_text(
                _('Messages you send here will be tooted to {}\nAccount: {}').format(api_url, uname))
            tgroup.set_profile_image(MASTODON_LOGO)
            ngroup.send_text(
                _('Here you will receive notifications from {}\nAccount: {}').format(api_url, uname))
            ngroup.set_profile_image(MASTODON_LOGO)

    @classmethod
    def logout_cmd(cls, ctx):
        contact = ctx.msg.get_sender_contact()
        addr = contact.addr
        if ctx.text:
            api_url, uname = ctx.text.split(maxsplit=1)
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname.lower(), addr)).fetchone()
        else:
            chat = cls.bot.get_chat(ctx.msg)
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE settings=?', (chat.id,)).fetchone()

        if acc:
            cls.delete_account(acc)
            cls.bot.get_chat(contact).send_text(_('You have logged out'))
        else:
            cls.bot.get_chat(ctx.msg).send_text(_('Unknow account'))

    @classmethod
    def direct_cmd(cls, ctx):
        if not ctx.text or ' ' in ctx.text:
            chat.send_text(_('Wrong Syntax'))
            return

        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE settings=?', (chat.id,)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        ctx.text = ctx.text.lstrip('@').lower()

        pv = cls.db.execute(
            'SELECT * FROM priv_chats WHERE api_url=? AND username=? AND contact=?', (acc['api_url'], acc['username'], ctx.text)).fetchone()
        if pv:
            cls.bot.get_chat(pv['id']).send_text(
                _('Chat already exists, send direct messages here'))
        else:
            g = cls.bot.create_group(
                '🇲 {} ({})'.format(ctx.text, acc['api_url']), [acc['addr']])
            cls.db.execute(
                'INSERT OR REPLACE INTO priv_chats VALUES (?,?,?,?)', (g.id, ctx.text, acc['api_url'], acc['username']))
            g.send_text(_('Private chat with {}\nYour account: {} ({})').format(
                ctx.text, acc['username'], acc['api_url']))
            m = cls.get_session(acc)
            contact = m.account_search(ctx.text, limit=1)
            if contact and contact[0]['acct'].lower() in (ctx.text, ctx.text.split('@')[0]):
                file_name = cls.bot.get_blobpath('mastodon-avatar.jpg')
                r = requests.get(contact[0]['avatar_static'])
                with open(file_name, 'wb') as fd:
                    fd.write(r.content)
                g.set_profile_image(file_name)

    @classmethod
    def reply_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        api_url, uname, toot_id, text = ctx.text.split(maxsplit=3)
        toot_id = int(toot_id)
        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE api_url=? AND username=?', (api_url, uname)).fetchone()
        if not acc:
            chat.send_text(_('Invalid instance or user'))
            return
        ctx.text = text
        cls.toot(ctx, acc, in_reply_to=toot_id)


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS accounts 
                (api_url TEXT,
                username TEXT,
                access_token TEXT NOT NULL,
                addr TEXT NOT NULL,
                status INTEGER NOT NULL,
                toots INTEGER NOT NULL,
                notifications INTEGER NOT NULL,
                settings INTEGER NOT NULL,
                last_notification TEXT,
                PRIMARY KEY(api_url, username))''')
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS priv_chats 
                (id INTEGER,
                contact TEXT NOT NULL,
                api_url TEXT NOT NULL,
                username TEXT NOT NULL,
                PRIMARY KEY(id))''')

    def execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def insert_user(self, user):
        self.execute(
            'INSERT OR REPLACE INTO accounts VALUES (?,?,?,?,?,?,?,?,?)', user)

    def delete_account(self, account):
        self.execute('DELETE FROM priv_chats WHERE api_url=? AND username=?',
                     (account['api_url'], account['username']))
        self.execute('DELETE FROM accounts WHERE api_url=? AND username=?',
                     (account['api_url'], account['username']))

    def close(self):
        self.db.close()


class Mastodon(mastodon.Mastodon):
    def mentions(self, id=None, account_id=None, max_id=None, min_id=None, since_id=None, limit=None):
        if max_id != None:
            max_id = self.__unpack_id(max_id)

        if min_id != None:
            min_id = self.__unpack_id(min_id)

        if since_id != None:
            since_id = self.__unpack_id(since_id)

        if account_id != None:
            account_id = self.__unpack_id(account_id)

        if id is None:
            exclude_types = ['follow', 'favourite', 'reblog', 'poll']
            params = self.__generate_params(locals(), ['id'])
            return self.__api_request('GET', '/api/v1/notifications', params)
        else:
            id = self.__unpack_id(id)
            url = '/api/v1/notifications/{0}'.format(str(id))
            return self.__api_request('GET', url)
