# -*- coding: utf-8 -*-
from urllib.request import quote

from simplebot import Plugin
import bs4
import requests


class WebGrabber(Plugin):

    name = 'WebGrabber'
    description = 'Provides the !web <url> command to request the given url. Ex. !web http://delta.chat.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!web <url>` el cual permite obtener la página web con la url dada. Ej. !web http://delta.chat.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!web', msg.text)
        if arg is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if not arg:
            chat.send_text(cls.description)
        else:
            try:
                headers = {'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}
                r = requests.get(arg, headers=headers, stream=True)
                TEMP_FILE = 'page.html'
                if 'text/html' in r.headers['content-type']:
                    soup = bs4.BeautifulSoup(r.text)
                    [t.extract() for t in soup(['script', 'meta', 'iframe', 'noscript'])]
                    comments = soup.find_all(text=lambda text:isinstance(text, bs4.Comment))
                    [comment.extract() for comment in comments]
                    for a in soup.find_all('a', attrs={'href':True}):
                        a['href'] = 'mailto:{}?subject={}&body={}'.format(cls.ctx.acc.get_self_contact().addr, quote('!web '), quote(a['href'], safe=''))
                    with open(TEMP_FILE, 'w') as fd:
                        fd.write(str(soup))
                    chat.send_file(TEMP_FILE, mime_type='text/html')
                else:
                    chat.send_text('Only html pages are allowed, but requested: %s' % r.headers['content-type'])
            except Exception as ex:
                cls.ctx.logger.exception(ex)
                chat.send_text('Falied to get the url: %s' % arg)
        return True
