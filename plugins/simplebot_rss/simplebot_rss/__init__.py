# -*- coding: utf-8 -*-
from threading import Thread, Event
from urllib.parse import quote_plus
import gettext
import os
import sqlite3

from jinja2 import Environment, PackageLoader
from simplebot import Plugin, Mode, PluginCommand
import feedparser
import html2text
import requests


feedparser.USER_AGENT = 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'
html2text.config.WRAP_LINKS = False


class RSS(Plugin):

    name = 'RSS'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('delay'):
            cls.cfg['delay'] = '300'
            cls.bot.save_config()

        cls.env = Environment(loader=PackageLoader(__name__, 'templates'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_rss', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.db = DBManager(
            os.path.join(cls.bot.get_dir(__name__), 'rss.db'))

        cls.worker = Thread(target=cls.check_feeds)
        cls.worker.deactivated = Event()
        cls.worker.start()

        cls.description = _('Subscribe to RSS and Atom links.')
        cls.commands = [
            PluginCommand('/rss/subscribe', ['<url>'], _(
                'Subscribe you to the given feed url'), cls.subscribe_cmd),
            PluginCommand('/rss/unsubscribe', ['<url>'], _(
                'Unsubscribe you from the given feed'), cls.unsubscribe_cmd),
            PluginCommand('/rss/list', [], _(
                'List feeds users are subscribed'), cls.list_cmd),
            PluginCommand('/rss/info', [], _(
                'Send this on a feed group to see the feed info'), cls.info_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.worker.deactivated.set()
        cls.worker.join()
        cls.db.close()

    @classmethod
    def subscribe_cmd(cls, ctx):
        Thread(target=cls._subscribe_cmd, args=(ctx,)).start()

    @classmethod
    def _subscribe_cmd(cls, ctx):
        url = ctx.text
        if not url.startswith('http'):
            url = 'http://'+url
        urls = [url]
        if url.endswith('/'):
            urls.append(url[:-1])
        else:
            urls.append(url+'/')
        if url.startswith('https'):
            urls.append('http'+url[5:])
            urls.append('http'+urls[1][5:])
        elif url.startswith('http'):
            urls.append('https'+url[4:])
            urls.append('https'+urls[1][4:])
        feed = cls.db.execute(
            'SELECT * FROM feeds WHERE url=? OR url=? OR url=? OR url=?', urls, 'one')
        sender = ctx.msg.get_sender_contact()
        if feed is None:  # new feed
            d = feedparser.parse(url)
            if d.get('bozo') == 1:
                chat = cls.bot.get_chat(ctx.msg)
                chat.send_text(_('Invalid feed url: {}').format(url))
                return
            title = d.feed.get('title')
            if not title:
                title = url
            description = d.feed.get('description', '')
            group = cls.bot.create_group('[RSS] '+title, [sender])
            cls.db.insert((url, title, description,
                           None, None, str(group.id), None))
            cls.set_image(group, d)
            group.send_text(
                _('Title:\n{}\n\nURL:\n{}\n\nDescription:\n{}').format(title, url, description))
        elif cls._is_subscribed(sender, feed):  # user is already subscribed
            chat = cls.bot.get_chat(ctx.msg)
            chat.send_text(_('You are alredy subscribed to that feed.'))
        else:  # feed exists
            d = feedparser.parse(feed['url'])
            group = cls.bot.create_group('[RSS] '+feed['title'], [sender])
            chats = '{} {}'.format(
                feed['chats'], group.id) if feed['chats'] else str(group.id)
            cls.db.execute(
                'UPDATE feeds SET chats=? WHERE url=?', (chats, feed['url']))
            cls.set_image(group, d)
            group.send_text(
                _('Title:\n{}\n\nURL:\n{}\n\nDescription:\n{}').format(feed['title'], feed['url'], feed['description']))
            if d.entries and feed['latest']:
                latest = tuple(map(int, feed['latest'].split()))
                d.entries = cls.get_old_entries(d, latest)
                entries = d.entries[-10:]
                if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
                    text = ''
                    for e in entries:
                        text += '{}:\n({})\n'.format(e.get('title',
                                                           _('NO TITLE')), e.get('link', '-'))
                        pub_date = e.get('published')
                        if pub_date:
                            text += '{}\n'.format(pub_date)
                        desc = e.get('description')
                        if desc:
                            text += '{}\n'.format(html2text.html2text(desc))
                        else:
                            text += '\n\n'
                    group.send_text(text)
                else:
                    html = cls.env.get_template('items.html').render(
                        plugin=cls, title=feed['title'], entries=entries)
                    cls.bot.send_html(group, html, cls.name,
                                      ctx.msg.text, ctx.mode)

    @classmethod
    def info_cmd(cls, ctx):
        g = cls.bot.get_chat(ctx.msg)
        for f in cls.db.execute('SELECT * FROM feeds'):
            if g.id in map(int, f['chats'].split()):
                g.send_text(
                    _('Title:\n{}\n\nURL:\n{}\n\nDescription:\n{}').format(f['title'], f['url'], f['description']))
                return
        g.send_text(_('This is not a feed group.'))

    @classmethod
    def list_cmd(cls, ctx):
        feeds = cls.db.execute('SELECT * FROM feeds')
        chat = cls.bot.get_chat(ctx.msg)
        if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
            feeds.sort(key=lambda f: len(f['chats'].split()))
            text = '{0} ({1}):\n\n'.format(cls.name, len(feeds))
            for f in feeds:
                scount = len(f['chats'].split())
                text += '{}\n({})\n* {} 👤\n{}\n\n'.format(
                    f['title'], f['url'], scount, f['description'])
            chat.send_text(text)
        else:
            feeds.sort(key=lambda f: len(f['chats'].split()), reverse=True)
            feeds = [(*f, quote_plus(f['url'])) for f in feeds]
            template = cls.env.get_template('feeds.html')
            addr = cls.bot.get_address()
            html = template.render(plugin=cls, feeds=feeds, bot_addr=addr)
            cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)

    @classmethod
    def unsubscribe_cmd(cls, ctx):
        Thread(target=cls._unsubscribe_cmd, args=(ctx,)).start()

    @classmethod
    def _unsubscribe_cmd(cls, ctx):
        url = ctx.text
        if not url.startswith('http'):
            url = 'http://'+url
        feed = cls.db.execute(
            'SELECT * FROM feeds WHERE url=?', (url,), 'one')
        chat = cls.bot.get_chat(ctx.msg)
        if feed is None:
            chat.send_text(_('Unknow feed: {}').format(url))
            return
        sender = ctx.msg.get_sender_contact()
        gid = cls._is_subscribed(sender, feed)
        if gid:
            ids = feed['chats'].split()
            ids.remove(gid)
            cls.db.execute(
                'UPDATE feeds SET chats=? WHERE url=?', (' '.join(ids), feed['url']))
            g = cls.bot.get_chat(int(gid))
            g.send_text(
                _('You had unsubscribed, you can remove this group'))
            g.remove_contact(cls.bot.get_contact())
        else:
            chat.send_text(_('You are not subscribed to: {}').format(url))

    @classmethod
    def get_new_entries(cls, d, date):
        new_entries = []
        for e in d.entries:
            d = e.get('published_parsed', e.get('updated_parsed'))
            if d is not None and d > date:
                new_entries.append(e)
        return new_entries

    @classmethod
    def get_old_entries(cls, d, date):
        old_entries = []
        for e in d.entries:
            d = e.get('published_parsed', e.get('updated_parsed'))
            if d is not None and d <= date:
                old_entries.append(e)
        return old_entries

    @classmethod
    def get_latest_date(cls, d):
        dates = (e.get('published_parsed', e.get('updated_parsed'))
                 for e in d.entries)
        dates = tuple(d for d in dates if d is not None)
        if len(dates) > 0:
            return max(dates)
        else:
            return None

    @classmethod
    def check_feeds(cls):
        while True:
            if cls.worker.deactivated.is_set():
                return
            cls.bot.logger.debug('Checking feeds')
            feeds = cls.db.execute('SELECT * FROM feeds')
            if feeds:
                me = cls.bot.get_contact()
                for feed in feeds:
                    if cls.worker.deactivated.is_set():
                        return
                    if not feed[5].strip():
                        cls.db.delete(feed['url'])
                        continue
                    d = feedparser.parse(
                        feed['url'], etag=feed['etag'], modified=feed['modified'])
                    if d.entries and feed['latest']:
                        latest = tuple(map(int, feed['latest'].split()))
                        d.entries = cls.get_new_entries(d, latest)
                    if not d.entries:
                        continue

                    entries = d.entries[-50:]
                    html = cls.env.get_template('items.html').render(
                        plugin=cls, title=feed['title'], entries=entries)
                    text = ''
                    for e in entries:
                        text += '{}:\n({})\n'.format(e.get('title',
                                                           _('NO TITLE')), e.get('link', '-'))
                        pub_date = e.get('published')
                        if pub_date:
                            text += '**{}**\n'.format(pub_date)
                        desc = e.get('description')
                        if desc:
                            text += '{}\n'.format(html2text.html2text(desc))
                        else:
                            text += '\n\n'

                    for gid in feed['chats'].split():
                        g = cls.bot.get_chat(int(gid))
                        members = g.get_contacts()
                        if me in members and len(members) > 1:
                            members.remove(me)
                            pref = cls.bot.get_preferences(members[0].addr)
                            if pref['mode'] in (Mode.TEXT, Mode.TEXT_HTMLZIP):
                                g.send_text(text)
                            else:
                                cls.bot.send_html(
                                    g, html, cls.name, '', pref['mode'])
                        else:
                            ids = feed['chats'].split()
                            ids.remove(gid)
                            cls.db.execute(
                                'UPDATE feeds SET chats=? WHERE url=?', (' '.join(ids), feed['url']))
                    latest = cls.get_latest_date(d)
                    if latest is not None:
                        latest = ' '.join(map(str, latest))
                    args = (d.get('etag'), d.get('modified', d.get('updated')),
                            latest, feed['url'])
                    cls.db.execute(
                        'UPDATE feeds SET etag=?, modified=?, latest=? WHERE url=?', args)
            cls.worker.deactivated.wait(cls.cfg.getint('delay'))

    @classmethod
    def _is_subscribed(cls, contact, feed):
        for gid in feed['chats'].split():
            g = cls.bot.get_chat(int(gid))
            if contact in g.get_contacts():
                return gid
        else:
            return None

    @classmethod
    def set_image(cls, group, d):
        img_link = d.feed.get('icon', d.feed.get(
            'logo', d.feed.get('image', {'href': None}).get('href')))
        if img_link is not None:
            img_link = img_link.rstrip('/')
        try:
            if img_link:
                r = requests.get(img_link)
                content_type = r.headers.get('content-type', '').lower()
                if 'image/png' in content_type:
                    file_name = 'group-img.png'
                elif 'image/jpeg' in content_type:
                    file_name = 'group-img.jpg'
                else:
                    file_name = os.path.basename(img_link).split('?')[
                        0].split('#')[0].lower()
                file_name = cls.bot.get_blobpath(file_name)
                with open(file_name, 'wb') as fd:
                    fd.write(r.content)
                group.set_profile_image(file_name)
        except Exception as ex:
            cls.bot.logger.exception(ex)


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        with self.db:
            self.db.execute(
                '''CREATE TABLE IF NOT EXISTS feeds
                       (url TEXT NOT NULL,
                        title TEXT,
                        description TEXT,
                        etag TEXT,
                        modified TEXT,
                        chats TEXT,
                        latest TEXT,
                        PRIMARY KEY(url))''')

    def execute(self, statement, args=(), get='all'):
        with self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def insert(self, feed):
        self.execute('INSERT INTO feeds VALUES (?,?,?,?,?,?,?)', feed)

    def delete(self, url):
        self.execute('DELETE FROM feeds WHERE url=?', (url,))

    def close(self):
        self.db.close()
