# -*- coding: utf-8 -*-
from urllib.request import urlopen

from simplebot import Plugin
from bs4 import BeautifulSoup

class GetDelta(Plugin):

    name = 'GetDelta'
    description = 'Provides the !getdelta command to get info and links for the latest release of Delta Chat (iOS, Desktop or Android). Ex. !getdelta Android.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando !getdelta para obtener información y enlaces de la última versión de Delta Chat(iOS, Desktop o Android). Ej. !getdelta Android.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!getdelta', msg.text)
        if arg is None:
            return False
        arg = arg.lower()
        if arg == 'ios':
            text = 'Delta Chat - iOS:\n\nhttps://testflight.apple.com/join/WVoYFOZe'
        else:
            platform = arg if arg == 'desktop' else 'android'
            page = urlopen('https://github.com/deltachat/deltachat-{}/releases'.format(platform)).read()
            latest = BeautifulSoup(page, 'html.parser').find('div', class_='label-latest')
            text = 'Delta Chat - {}({}):\n\n'.format(platform.capitalize(), latest.ul.a['title'].strip())
            text += latest.find('div', class_='markdown-body').get_text()
            for box in list(latest.find_all('div', class_='Box-body'))[:-2]:
                text += '\nhttps://github.com'+box.a['href']
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True
