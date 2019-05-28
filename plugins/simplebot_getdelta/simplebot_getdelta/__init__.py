# -*- coding: utf-8 -*-
from urllib.request import urlopen

from simplebot import Plugin
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader, select_autoescape


class GetDelta(Plugin):

    name = 'GetDelta'
    description = 'Get info and links for the latest release of Delta Chat.'
    long_description = 'You can get it sending the command !getdelta to this bot.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!getdelta'

    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        if ctx.locale == 'es':
            cls.description = 'Obtén enlaces de descarga e información sobre la última versión de Delta Chat.'
            cls.long_description = 'Puedes obtenerlo enviandole el comando !getdelta a este bot.'
            cls.NOSCRIPT = 'Necesitas un navegador que soporte JavaScript para poder usar esta funcionalidad.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!getdelta', msg.text)
        if arg is None:
            return False
        arg = arg.lower()
        ios = 'https://testflight.apple.com/join/WVoYFOZe'
        android = cls.get_info('android')
        desktop = cls.get_info('desktop')        
        chat = cls.ctx.acc.create_chat_by_message(msg)
        template = cls.env.get_template('index.html')
        html = template.render(plugin=cls, platforms=[('Android',android), ('iOS',ios), ('Desktop',desktop)])
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True

    @staticmethod
    def get_info(platform):
        page = urlopen('https://github.com/deltachat/deltachat-{}/releases'.format(platform)).read()
        latest = BeautifulSoup(page, 'html.parser').find('div', class_='label-latest')
        text = '{}:<br>'.format(latest.ul.a['title'].strip())
        text += latest.find('div', class_='markdown-body').get_text()
        for box in list(latest.find_all('div', class_='Box-body'))[:-2]:
            text += '<br>https://github.com{}'.format(box.a['href'])
        return text
