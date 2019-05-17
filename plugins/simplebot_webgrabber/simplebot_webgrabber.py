# -*- coding: utf-8 -*-
from simplebot import Plugin

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
                    with open(TEMP_FILE, 'wb') as fd:
                        for chunk in r.iter_content(chunk_size=128):
                            fd.write(chunk)
                    chat.send_file(TEMP_FILE, mime_type='text/html')
                else:
                    chat.send_text('Only html pages are allowed, but requested: %s' % r.headers['content-type'])
            except:
                chat.send_text('Falied to get the url: %s' % arg)
        return True
