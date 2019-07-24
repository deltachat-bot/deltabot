# -*- coding: utf-8 -*-
from urllib.request import urlopen
import gettext
import os

from simplebot import Plugin
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader, select_autoescape


class GetDelta(Plugin):

    name = 'GetDelta'
   version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!getdelta'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
        )
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_getdelta', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_getdelta', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin-description')
        cls.long_description = _('plugin-long-description')
        cls.NOSCRIPT = _('noscript_msg')
    
    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!getdelta', msg.text)
        if arg is None:
            return False
        arg = arg.lower()
        ios = '<a href="https://testflight.apple.com/join/WVoYFOZe">Delta Chat on TestFlight</a>'
        android = cls.get_info('android')
        desktop = cls.get_info('desktop')        
        chat = cls.ctx.acc.create_chat_by_message(msg)
        template = cls.env.get_template('index.html')
        html = template.render(plugin=cls, platforms=[('iOS',ios), ('Android',android), ('Desktop',desktop)])
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True

    @staticmethod
    def get_info(platform):
        page = urlopen('https://github.com/deltachat/deltachat-{}/releases'.format(platform)).read()
        soup = BeautifulSoup(page, 'html.parser')
        latest = soup.find('div', class_='label-latest').find('div', class_='release-main-section')
        for a in latest.find_all('a', attrs={'href':True}):
            if a['href'].startswith('/'):
                a['href'] = 'https://github.com'+a['href']
        return str(latest)
