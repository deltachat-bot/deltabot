# -*- coding: utf-8 -*-
from enum import IntEnum, Enum
from threading import Thread, Event
from urllib.parse import quote_plus
import gettext
import os
import sqlite3

from simplebot import Plugin, PluginCommand, PluginFilter, Mode
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader
from pydub import AudioSegment
import mastodon
import requests
import deltachat as dc


MASTODON_LOGO = os.path.join(os.path.dirname(__file__), 'mastodon-logo.png')


class Status(IntEnum):
    DISABLED = 0
    ENABLED = 1


class Visibility(str, Enum):
    DIRECT = 'direct'  # post will be visible only to mentioned users
    PRIVATE = 'private'  # post will be visible only to followers
    UNLISTED = 'unlisted'  # post will be public but not appear on the public timeline
    PUBLIC = 'public'  # post will be public


v2emoji = {Visibility.DIRECT: '✉', Visibility.PRIVATE: '🔒',
           Visibility.UNLISTED: '🔓', Visibility.PUBLIC: '🌎'}


def rmprefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]


class MastodonBridge(Plugin):

    name = 'Mastodon Bridge'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        save = False
        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('delay'):
            cls.cfg['delay'] = '20'
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
            PluginCommand('/masto/enable', [],
                          _('Enable the Mastodon bridge again'), cls.enable_cmd),
            PluginCommand('/masto/disable', [],
                          _('Disable the Mastodon bridge, you will stop receiving messages from Mastodon'), cls.disable_cmd),
            PluginCommand('/masto/direct', ['<user>'],
                          _('Start a private chat with the given Mastodon user'), cls.direct_cmd),
            PluginCommand('/masto/reply', ['<id>', '<text>'],
                          _('Reply to a toot with the given id'), cls.reply_cmd),
            PluginCommand('/masto/star', ['<id>'],
                          _('Mark as favourite the toot with the given id'), cls.star_cmd),
            PluginCommand('/masto/boost', ['<id>'],
                          _('Boost the toot with the given id'), cls.boost_cmd),
            PluginCommand('/masto/context', ['<id>'],
                          _('Get the context of the toot with the given id'), cls.context_cmd),
            PluginCommand('/masto/follow', ['<id>'],
                          _('Follow the user with the given id'), cls.follow_cmd),
            PluginCommand('/masto/unfollow', ['<id>'],
                          _('Unfollow the user with the given id'), cls.unfollow_cmd),
            PluginCommand('/masto/mute', ['<id>'],
                          _('Mute the user with the given id'), cls.mute_cmd),
            PluginCommand('/masto/unmute', ['<id>'],
                          _('Unmute the user with the given id'), cls.unmute_cmd),
            PluginCommand('/masto/whois', ['<id>'],
                          _('See the profile of the given user'), cls.whois_cmd),
            PluginCommand('/masto/timeline', ['<timeline>'],
                          _('Get latest entries from the given timeline'), cls.timeline_cmd),
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
    def get_user(cls, m, user_id):
        user = None
        if user_id.isdigit():
            user = m.account(user_id)
        else:
            user_id = user_id.lstrip('@').lower()
            ids = (user_id, user_id.split('@')[0])
            for a in m.account_search(user_id):
                if a.acct.lower() in ids:
                    user = a
                    break
        return user

    @classmethod
    def toot(cls, ctx, acc, visibility=None, in_reply_to=None):
        m = cls.get_session(acc)
        if ctx.msg.is_image() or ctx.msg.is_gif() or ctx.msg.is_video() or ctx.msg._view_type in (dc.const.DC_MSG_AUDIO, dc.const.DC_MSG_VOICE):
            if ctx.msg.filename.endswith('.aac'):
                aac_file = AudioSegment.from_file(ctx.msg.filename, 'aac')
                filename = ctx.msg.filename[:-4]+'.mp3'
                aac_file.export(filename, format='mp3')
            else:
                filename = ctx.msg.filename
            media = [m.media_post(filename).id]
            if in_reply_to:
                m.status_reply(m.status(in_reply_to), ctx.text,
                               media_ids=media, visibility=visibility)
            else:
                m.status_post(ctx.text, media_ids=media, visibility=visibility)
        elif ctx.text:
            if in_reply_to:
                m.status_reply(m.status(in_reply_to),
                               ctx.text, visibility=visibility)
            else:
                m.status_post(ctx.text, visibility=visibility)
        else:
            cls.bot.get_chat(ctx.msg).send_text(_('Unsuported message type'))

    @staticmethod
    def parse_url(url):
        api_url, url = url.split('@', maxsplit=1)
        uname, toot_id = url.split('/', maxsplit=1)
        return (api_url, uname, toot_id)

    @staticmethod
    def get_text(html):
        soup = BeautifulSoup(html, 'html.parser')
        for br in soup('br'):
            br.replace_with('\n')
        for p in soup('p'):
            p.replace_with(p.get_text()+'\n\n')
        return soup.get_text()

    @staticmethod
    def toots2text(toots, url):
        for t in reversed(toots):
            if t.reblog:
                a = t.reblog.account
                text = '{} (@{}):\n🔁 {} (@{})\n\n'.format(
                    a.display_name, a.acct, t.account.display_name, t.account.acct)
            else:
                text = '{} (@{}):\n\n'.format(
                    t.account.display_name, t.account.acct)

            media_urls = '\n'.join(
                media.url for media in t.media_attachments)
            if media_urls:
                text += media_urls + '\n\n'

            soup = BeautifulSoup(
                t.content, 'html.parser')
            if t.mentions:
                accts = {e.url: '@' + e.acct
                         for e in t.mentions}
                for a in soup('a', class_='u-url'):
                    a.string = accts[a['href']]
            for br in soup('br'):
                br.replace_with('\n')
            for p in soup('p'):
                p.replace_with(p.get_text()+'\n\n')
            text += soup.get_text()

            text += '\n\n[{}] {}{}'.format(
                v2emoji[t.visibility], url, t.id)

            yield text

    @classmethod
    def toots2html(cls, toots, url, template='items.html', **kargs):
        for t in toots:
            soup = BeautifulSoup(
                t.content, 'html.parser')
            if t.mentions:
                accts = {e.url: '@' + e.acct for e in t.mentions}
                for a in soup('a', class_='u-url'):
                    a.string = accts[a['href']]
            t['content'] = str(soup)

        me = cls.bot.get_contact().addr
        return cls.env.get_template(template).render(
            plugin=cls, toots=toots, bot_addr=me, url=quote_plus(url), v2emoji=v2emoji, **kargs)

    @classmethod
    def get_account(cls, chat):
        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE notifications=? OR settings=? OR toots=?', (chat.id,)*3).fetchone()
        if not acc:
            pv = cls.db.execute(
                'SELECT api_url, username FROM priv_chats WHERE id=?', (chat.id,))
            if pv:
                acc = cls.db.execute(
                    'SELECT * FROM accounts WHERE api_url=? AND username=?', (pv['api_url'], pv['username']))
        return acc

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
                url = '{}@{}/'.format(acc['api_url'], acc['username'])
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
                                ment[0].id, acc['api_url'], acc['username']))
                        max_id = ment[-1]
                        for mention in ment:
                            if not mention.type == 'mention':
                                continue
                            s = mention.status
                            if s.visibility == Visibility.DIRECT and len(s.mentions) == 1:
                                dmsgs.append(s)
                            else:
                                mentions.append(s)
                    for dm in reversed(dmsgs):
                        acct = dm.account.acct
                        text = '{} (@{}):\n\n'.format(
                            dm.account.display_name, acct)

                        media_urls = '\n'.join(
                            media.url for media in dm.media_attachments)
                        if media_urls:
                            text += media_urls + '\n\n'

                        soup = BeautifulSoup(dm.content, 'html.parser')
                        accts = {e.url: '@'+e.acct
                                 for e in dm.mentions}
                        for a in soup('a', class_='u-url'):
                            a.string = accts[a['href']]
                        for br in soup('br'):
                            br.replace_with('\n')
                        for p in soup('p'):
                            p.replace_with(p.get_text()+'\n\n')
                        text += soup.get_text()
                        text += '\n\nID: {}{}'.format(url, dm.id)

                        pv = cls.db.execute(
                            'SELECT * FROM priv_chats WHERE api_url=? AND username=? AND contact=?', (acc['api_url'], acc['username'], acct.lower())).fetchone()
                        if pv:
                            g = cls.bot.get_chat(pv['id'])
                            if g is None:
                                cls.db.execute(
                                    'DELETE FROM priv_chats WHERE id=?', (pv['id'],))
                            else:
                                g.send_text(text)
                        else:
                            g = cls.bot.create_group(
                                '🇲 {} ({})'.format(acct, rmprefix(acc['api_url'], 'https://')), [acc['addr']])
                            cls.db.execute(
                                'INSERT INTO priv_chats VALUES (?,?,?,?)', (g.id, acct.lower(), acc['api_url'], acc['username']))

                            r = requests.get(dm.account.avatar_static)
                            fname = r.url.split(
                                '/').pop().split('?')[0].split('#')[0]
                            if '.' not in fname:
                                fname = 'mastodon-avatar.jpg'
                            fname = cls.bot.get_blobpath(fname)
                            with open(fname, 'wb') as fd:
                                fd.write(r.content)

                            g.set_profile_image(fname)
                            g.send_text(text)

                    chat = cls.bot.get_chat(acc['notifications'])
                    if mentions:
                        pref = cls.bot.get_preferences(acc['addr'])
                        if pref['mode'] in (Mode.TEXT, Mode.TEXT_HTMLZIP):
                            chat.send_text('\n\n―――――――――――――――\n\n'.join(
                                cls.toots2text(mentions, url)))
                        else:
                            html = cls.toots2html(mentions, url)
                            cls.bot.send_html(
                                chat, html, cls.name, '', pref['mode'])
                except mastodon.MastodonUnauthorizedError:
                    cls.delete_account(acc)
                    cls.bot.get_chat(acc['addr']).send_text(
                        _('You have logged out from Mastodon'))
                except Exception as ex:
                    cls.bot.logger.exception(ex)
                cls.worker.deactivated.wait(1)
            cls.worker.deactivated.wait(cls.cfg.getint('delay'))

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)

        account = cls.db.execute(
            'SELECT * FROM accounts WHERE toots=?', (chat.id,)).fetchone()
        if account:
            ctx.processed = True
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
        uname = m.me().acct.lower()

        old_user = cls.db.execute(
            'SELECT * FROM accounts WHERE username=? AND api_url=?', (uname, api_url)).fetchone()
        if old_user:
            chat.send_text(_('Account already in use'))
        else:
            n = m.notifications(limit=1)
            last_notification = n[0].id if n else None

            addr = ctx.msg.get_sender_contact().addr
            tgroup = cls.bot.create_group(
                'Toot to {}'.format(rmprefix(api_url, 'https://')), [addr])
            ngroup = cls.bot.create_group(
                'Notifications ({})'.format(rmprefix(api_url, 'https://')), [addr])
            sgroup = cls.bot.create_group(
                'Settings ({})'.format(rmprefix(api_url, 'https://')), [addr])

            cls.db.insert_user(
                (api_url, uname, access_token, addr, Status.ENABLED, tgroup.id, ngroup.id, sgroup.id, last_notification))

            sgroup.set_profile_image(MASTODON_LOGO)
            tgroup.set_profile_image(MASTODON_LOGO)
            ngroup.set_profile_image(MASTODON_LOGO)
            sgroup.send_text(
                _('Here you can send commands for account: {} at {}\n\nTo logout from the bridge just leave this group').format(uname, api_url))
            tgroup.send_text(
                _('Messages you send here will be tooted to {}\nAccount: {}').format(api_url, uname))
            ngroup.send_text(
                _('Here you will receive notifications from {}\nAccount: {}').format(api_url, uname))

    @classmethod
    def logout_cmd(cls, ctx):
        contact = ctx.msg.get_sender_contact()
        addr = contact.addr
        if ctx.text:
            api_url, uname = ctx.text.split(maxsplit=1)
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname.lower(), addr)).fetchone()
        else:
            acc = cls.get_account(cls.bot.get_chat(ctx.msg))

        if acc:
            cls.delete_account(acc)
            cls.bot.get_chat(contact).send_text(
                _('You have logged out from Mastodon'))
        else:
            cls.bot.get_chat(ctx.msg).send_text(_('Unknow account'))

    @classmethod
    def enable_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        if acc['status'] != Status.ENABLED:
            cls.db.execute('UPDATE accounts SET status=? WHERE api_url=? AND username=?',
                           (Status.ENABLED, acc['api_url'], acc['username']))
        chat.send_text(_('Account enabled'))

    @classmethod
    def disable_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        if acc['status'] != Status.DISABLED:
            cls.db.execute('UPDATE accounts SET status=? WHERE api_url=? AND username=?',
                           (Status.DISABLED, acc['api_url'], acc['username']))
        chat.send_text(_('Account disabled'))

    @classmethod
    def direct_cmd(cls, ctx):
        if not ctx.text or ' ' in ctx.text:
            chat.send_text(_('Wrong Syntax'))
            return

        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
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
                '🇲 {} ({})'.format(ctx.text, rmprefix(acc['api_url'], 'https://')), [acc['addr']])
            cls.db.execute(
                'INSERT OR REPLACE INTO priv_chats VALUES (?,?,?,?)', (g.id, ctx.text, acc['api_url'], acc['username']))
            m = cls.get_session(acc)
            contact = m.account_search(ctx.text, limit=1)
            if contact and contact[0].acct.lower() in (ctx.text, ctx.text.split('@')[0]):
                file_name = cls.bot.get_blobpath('mastodon-avatar.jpg')
                r = requests.get(contact[0].avatar_static)
                with open(file_name, 'wb') as fd:
                    fd.write(r.content)
                g.set_profile_image(file_name)
            g.send_text(_('Private chat with {}\nYour account: {} ({})').format(
                ctx.text, acc['username'], acc['api_url']))

    @classmethod
    def reply_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        url, text = ctx.text.split(maxsplit=1)
        api_url, uname, toot_id = cls.parse_url(url)
        addr = ctx.msg.get_sender_contact().addr

        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(_('Invalid toot id'))
            return

        ctx.text = text
        cls.toot(ctx, acc, in_reply_to=toot_id)

    @classmethod
    def star_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        api_url, uname, toot_id = cls.parse_url(ctx.text)
        addr = ctx.msg.get_sender_contact().addr

        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(_('Invalid toot id'))
            return

        m = cls.get_session(acc)
        m.status_favourite(toot_id)

    @classmethod
    def boost_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        api_url, uname, toot_id = cls.parse_url(ctx.text)
        addr = ctx.msg.get_sender_contact().addr

        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(_('Invalid toot id'))
            return

        m = cls.get_session(acc)
        m.status_reblog(toot_id)

    @classmethod
    def context_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        api_url, uname, toot_id = cls.parse_url(ctx.text)
        addr = ctx.msg.get_sender_contact().addr

        acc = cls.db.execute(
            'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(_('Invalid toot id'))
            return

        m = cls.get_session(acc)
        toots = m.status_context(toot_id)['ancestors']
        if toots:
            url = '{}@{}/'.format(acc['api_url'], acc['username'])
            if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
                chat.send_text('\n\n―――――――――――――――\n\n'.join(
                    cls.toots2text([toots[-1]], url)))
            else:
                html = cls.toots2html([toots[-1]], url)
                cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)
        else:
            chat.send_text(_('Nothing found'))

    @classmethod
    def follow_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if acc:
            acc_id = ctx.text
        else:
            api_url, uname, acc_id = cls.parse_url(ctx.text)
            addr = ctx.msg.get_sender_contact().addr
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        m = cls.get_session(acc)
        if not acc_id.isdigit():
            acc_id = cls.get_user(m, acc_id)
            if acc_id is None:
                chat.send_text(_('Invalid id'))
                return
        m.account_follow(acc_id)
        chat.send_text(_('User followed'))

    @classmethod
    def unfollow_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if acc:
            acc_id = ctx.text
        else:
            api_url, uname, acc_id = cls.parse_url(ctx.text)
            addr = ctx.msg.get_sender_contact().addr
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        m = cls.get_session(acc)
        if not acc_id.isdigit():
            acc_id = cls.get_user(m, acc_id)
            if acc_id is None:
                chat.send_text(_('Invalid id'))
                return
        m.account_unfollow(acc_id)
        chat.send_text(_('User unfollowed'))

    @classmethod
    def mute_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if acc:
            acc_id = ctx.text
        else:
            api_url, uname, acc_id = cls.parse_url(ctx.text)
            addr = ctx.msg.get_sender_contact().addr
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        m = cls.get_session(acc)
        if not acc_id.isdigit():
            acc_id = cls.get_user(m, acc_id)
            if acc_id is None:
                chat.send_text(_('Invalid id'))
                return
        m.account_mute(acc_id)
        chat.send_text(_('User muted'))

    @classmethod
    def unmute_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if acc:
            acc_id = ctx.text
        else:
            api_url, uname, acc_id = cls.parse_url(ctx.text)
            addr = ctx.msg.get_sender_contact().addr
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        m = cls.get_session(acc)
        if not acc_id.isdigit():
            acc_id = cls.get_user(m, acc_id)
            if acc_id is None:
                chat.send_text(_('Invalid id'))
                return
        m.account_unmute(acc_id)
        chat.send_text(_('User unmuted'))

    @classmethod
    def whois_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if acc:
            acc_id = ctx.text
        else:
            api_url, uname, acc_id = cls.parse_url(ctx.text)
            addr = ctx.msg.get_sender_contact().addr
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        m = cls.get_session(acc)
        user = cls.get_user(m, acc_id)
        if user is None:
            chat.send_text(_('Invalid id'))
            return

        url = '{}@{}/'.format(acc['api_url'], acc['username'])
        toots = m.account_statuses(user.id)
        if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
            text = '{} (@{}):\n\n'.format(user.display_name, user.acct)
            fields = ''
            for f in user.fields:
                fields += '{}: {}\n'.format(cls.get_text(f.name),
                                            cls.get_text(f.value))
            if fields:
                text += fields+'\n\n'
            text += cls.get_text(user.note)
            text += '\n\nToots: {}\nFollowing: {}\nFollowers: {}\n\n'.format(
                user.statuses_count, user.following_count, user.followers_count)

            text += '\n\n―――――――――――――――\n\n'.join(
                cls.toots2text(toots, url))

            chat.send_text(text)
        else:
            html = cls.toots2html(
                toots, url, template='profile.html', user=user)
            cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)

    @classmethod
    def timeline_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        acc = cls.get_account(chat)
        if acc:
            timeline = ctx.text
        else:
            api_url, uname, timeline = cls.parse_url(ctx.text)
            addr = ctx.msg.get_sender_contact().addr
            acc = cls.db.execute(
                'SELECT * FROM accounts WHERE api_url=? AND username=? AND addr=?', (api_url, uname, addr)).fetchone()
        if not acc:
            chat.send_text(
                _('You must send that command in you Mastodon account settings chat'))
            return

        m = cls.get_session(acc)
        if timeline.startswith('#'):
            toots = m.timeline('tag/' + timeline[1:])
        else:
            toots = m.timeline(timeline)

        url = '{}@{}/'.format(acc['api_url'], acc['username'])

        if toots:
            if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
                chat.send_text('\n\n―――――――――――――――\n\n'.join(
                    cls.toots2text(toots, url)))
            else:
                html = cls.toots2html(toots, url)
                cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)
        else:
            chat.send_text(_('Nothing found for {}').format(timeline))


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
