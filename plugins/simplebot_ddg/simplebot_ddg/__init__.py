# -*- coding: utf-8 -*-
from urllib.request import urlopen
from urllib.parse import quote_plus

from simplebot import Plugin
from bs4 import BeautifulSoup
from jinja2 import Environment, PackageLoader, select_autoescape


env = Environment(
    loader=PackageLoader('simplebot_ddg', 'templates'),
    autoescape=select_autoescape(['html', 'xml'])
)


class DuckDuckGo(Plugin):

    name = 'DuckDuckGo'
    description = 'Provides the !ddg <text> command to search <text> in DuckDuckGo. Ex. !ddg free as in freedom.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    NOT_FOUND = 'No results found for: "{}"'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!ddg <texto>` para buscar en DuckDuckGo(buscador de Internet). Ej. !ddg que es software libre?.'
            cls.NOT_FOUND = 'No se encontraron resultados para: "{}"'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!ddg', msg.text)
        if arg is None:
            return False
        if arg:
            text = ''
            page = urlopen('https://duckduckgo.com/html?q=%s' % quote_plus(arg)).read()
            results = BeautifulSoup(page, 'html.parser').find_all('div', class_='result')[:6]
            if not results:
                text = cls.NOT_FOUND.format(arg)
            for r in results:
                text += r.h2.a.get_text().strip() + '\n'
                text += r.find('a', class_='result__url').get_text().strip()+'\n'
                text += r.find('a', class_='result__snippet').get_text() +'\n\n'
        else:
            template = env.get_template('help.html')
            text = template.render(ctx=cls)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True
