# -*- coding: utf-8 -*-
from threading import Thread, RLock
from urllib.parse import quote_plus
from urllib.request import urlretrieve
import gettext
import os
import sqlite3
import time

from jinja2 import Environment, PackageLoader
from simplebot import Plugin
import deltachat as dc
import feedparser


class RSS(Plugin):

    name = 'RSS'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        cls.temp_file = os.path.join(cls.bot.basedir, cls.name)

        cls.cfg = cls.bot.get_config(__name__)
        if not cls.cfg.get('delay'):
            cls.cfg['delay'] = '600'
            cls.bot.save_config()

        cls.env = Environment(loader=PackageLoader(__name__, 'templates'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_rss', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        db_path = os.path.join(cls.bot.basedir, 'rss.db')
        cls.db = DBManager(db_path)

        cls.worker = Thread(target=cls.check_feeds)
        cls.worker.start()

        cls.description = _('Suscribe to RSS and Atom links.')
        cls.long_description = _(
            'To unsubscribe just leave the feed is group or remove the bot from the group.')
        cls.commands = [
            ('/rss/subscribe', ['<url>'],
             _('Suscribe you to the given feed url'), cls.subscribe_cmd),
            ('/rss/list', [],
             _('List feeds users are subscribed'), cls.list_cmd),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        # TODO: stop threads
        cls.db.close()

    @classmethod
    def subscribe_cmd(cls, msg, url):
        if not url.startswith('http'):
            url = 'http://'+url
        feed = cls.db.execute(
            'SELECT * FROM feeds WHERE url=?', (url,), 'one')
        sender = msg.get_sender_contact()
        if feed is None:  # new feed
            d = feedparser.parse(url)
            if d.get('bozo') or not d.feed:
                chat = cls.bot.get_chat(msg)
                chat.send_text(_('Invalid feed url: {}').format(url))
            title = d.feed.get('title')
            if not title:
                title = url
            description = d.feed.get('description', '')
            group = cls.bot.create_group('[RSS] '+title, [sender])
            cls.db.insert((url, title, description,
                           None, None, str(group.id), None))
            group.send_text(
                _('Title:\n{}\n\nDescription:\n{}').format(title, description))
            img_link = d.feed.get('image', {'href': None}).get('href')
            cls.set_image(group, img_link)
        elif cls._is_subscribed(sender, feed):  # user is already subscribed
            chat = cls.bot.get_chat(msg)
            chat.send_text(_('You are alredy subscribed to that feed.'))
        else:  # feed exists
            d = feedparser.parse(url)
            group = cls.bot.create_group('[RSS] '+feed[1], [sender])
            chats = '{} {}'.format(
                feed[5], group.id) if feed[5] else str(group.id)
            cls.db.execute(
                'UPDATE feeds SET chats=? WHERE url=?', (chats, feed[0]))
            group.send_text(
                _('Title:\n{}\n\nDescription:\n{}').format(feed[1], feed[2]))
            img_link = d.feed.get('image', {'href': None}).get('href')
            cls.set_image(group, img_link)
            if d.entries and feed[6]:
                latest = tuple(map(int, feed[6].split()))
                d.entries = cls.get_old_entries(d, latest)
                html = cls.env.get_template('items.html').render(
                    plugin=cls, title=feed[1], entries=d.entries[-100:])
                cls.bot.send_html(group, html, cls.temp_file, msg.user_agent)

    @classmethod
    def list_cmd(cls, msg, args):
        feeds = [(quote_plus(f[0]), *f[1:])
                 for f in cls.db.execute('SELECT * FROM feeds')]
        template = cls.env.get_template('feeds.html')
        addr = cls.bot.get_address()
        html = template.render(plugin=cls, feeds=feeds, bot_addr=addr)
        chat = cls.bot.get_chat(msg)
        cls.bot.send_html(chat, html, cls.temp_file, msg.user_agent)

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
            # TODO: check if must stop
            feeds = cls.db.execute('SELECT * FROM feeds')
            if feeds:
                me = cls.bot.get_contact()
                for feed in feeds:
                    # TODO: check if must stop
                    if not feed[5].strip():
                        cls.db.delete(feed[0])
                        continue
                    d = feedparser.parse(
                        feed[0], etag=feed[3], modified=feed[4])
                    if d.entries and feed[6]:
                        latest = tuple(map(int, feed[6].split()))
                        d.entries = cls.get_new_entries(d, latest)
                    if not d.entries:
                        continue
                    html = cls.env.get_template('items.html').render(
                        plugin=cls, title=feed[1], entries=d.entries[-100:])
                    html_file = cls.temp_file+'.html'
                    with open(html_file, 'w') as fd:
                        fd.write(html)
                    for gid in feed[5].split():
                        g = cls.bot.get_chat(int(gid))
                        members = g.get_contacts()
                        if me in members and len(members) > 1:
                            g.send_file(html_file,
                                        mime_type='text/html')
                        else:
                            ids = feed[5].split()
                            ids.remove(gid)
                            cls.db.execute(
                                'UPDATE feeds SET chats=? WHERE url=?', (' '.join(ids), feed[0]))
                    latest = cls.get_latest_date(d)
                    if latest is not None:
                        latest = ' '.join(map(str, latest))
                    args = (d.get('etag'), d.get('modified', d.get('updated')),
                            latest, feed[0])
                    cls.db.execute(
                        'UPDATE feeds SET etag=?, modified=?, latest=? WHERE url=?', args)
            time.sleep(cls.cfg.getint('delay'))  # TODO: check if must stop

    @classmethod
    def _is_subscribed(cls, contact, feed):
        for g in (cls.bot.get_chat(int(gid)) for gid in feed[5].split()):
            if contact in g.get_contacts():
                return True
        else:
            return False

    @classmethod
    def set_image(cls, group, img_link):
        try:
            if img_link:
                image = os.path.join(cls.bot.get_blobdir(), 'image.jpg')
                urlretrieve(img_link, image)
                dc.capi.lib.dc_set_chat_profile_image(
                    cls.bot.account._dc_context, group.id, dc.account.as_dc_charpointer(image))
        except Exception as ex:
            cls.bot.logger.exception(ex)


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = RLock()
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
        with self.lock, self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def insert(self, feed):
        self.execute('INSERT INTO feeds VALUES (?,?,?,?,?,?,?)', feed)

    def delete(self, url):
        self.execute('DELETE FROM feeds WHERE url=?', (url,))

    def close(self):
        self.db.close()
