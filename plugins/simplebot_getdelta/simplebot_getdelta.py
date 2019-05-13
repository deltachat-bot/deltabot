# -*- coding: utf-8 -*-
from urllib.request import urlopen

from simplebot import Plugin
from bs4 import BeautifulSoup

class GetDelta(Plugin):

    name = 'GetDelta'
    description = 'Provides the !getdelta command to get info and links for the latest release of Delta Chat. Ex. !getdelta.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando !getdelta para obtener información y enlaces de la última versión de Delta Chat. Ej. !getdelta.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!getdelta', msg.text)
        if arg is None:
            return False
        page = urlopen('https://github.com/deltachat/deltachat-android/releases').read()
        latest = BeautifulSoup(page, 'html.parser').find('div', class_='label-latest')
        text = latest.ul.a['title']
        text += latest.find('div', class_='markdown-body').get_text()
        text += '\nhttps://github.com'+latest.find('div', class_='Box-body').a['href']
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True
