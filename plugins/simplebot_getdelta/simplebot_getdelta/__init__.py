# -*- coding: utf-8 -*-
from urllib.request import urlopen
import gettext
import os

from simplebot import Plugin
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader, select_autoescape


class GetDelta(Plugin):

    name = 'GetDelta'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        cls.TEMP_FILE = os.path.join(cls.bot.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
        )
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_getdelta', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()
        cls.description = _(
            'Get info and links for the latest releases of Delta Chat.')
        cls.commands = [('/getdelta', [], _(
            'Will send an html file with info about '), cls.getdelta_cmd)]
        cls.bot.add_commands(cls.commands)
        cls.NOSCRIPT = _(
            'You need a browser with JavaScript support for this page to work correctly.')

    @classmethod
    def getdelta_cmd(cls, msg, text):
        ios = '<a href="https://testflight.apple.com/join/WVoYFOZe">Delta Chat on TestFlight</a>'
        android = cls.get_info('android')
        desktop = cls.get_info('desktop')
        chat = cls.bot.get_chat(msg)
        template = cls.env.get_template('index.html')
        html = template.render(plugin=cls, platforms=[(
            'iOS', ios), ('Android', android), ('Desktop', desktop)])
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.bot.get_chat(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')

    @staticmethod
    def get_info(platform):
        page = urlopen(
            'https://github.com/deltachat/deltachat-{}/releases'.format(platform)).read()
        soup = BeautifulSoup(page, 'html.parser')
        latest = soup.find(
            'div', class_='label-latest').find('div', class_='release-main-section')
        for a in latest.find_all('a', attrs={'href': True}):
            if a['href'].startswith('/'):
                a['href'] = 'https://github.com'+a['href']
        return str(latest)
