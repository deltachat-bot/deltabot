# -*- coding: utf-8 -*-
import os

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin
import translators as ts


class Translator(Plugin):

    name = 'Translator'
    description = 'Translate text.'
    long_description = 'Example: !tr en es hello world'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!tr'

    #NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        # cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        # cls.env = Environment(
        #     loader=PackageLoader(__name__, 'templates'),
        #     autoescape=select_autoescape(['html', 'xml'])
        # )
        # if ctx.locale == 'es':
        #     cls.description = 'Un plugin sencillo para que el bot repita lo que envíes como un eco.'
        #     cls.long_description = 'Para usarlo puedes enviar un mensaje que comience con !echo, por ejemplo: !echo hola mundo y el bot responderá "hola mundo", esto permite comprobar de forma rápida que el bot está funcionando.'
        #     cls.NOSCRIPT = 'Necesitas un navegador que soporte JavaScript para poder usar esta funcionalidad.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args(cls.cmd, msg.text)
        if arg is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if not arg:
            # with open(cls.TEMP_FILE, 'w') as fd:
            #     fd.write(cls.env.get_template('index.html').render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
            # chat.send_file(cls.TEMP_FILE, mime_type='text/html')
            chat.send_text(cls.long_description)
        else:
            text = arg.split()
            l1, l2, text = text[0], text[1], ' '.join(text[2:])
            text = ts.google(text=text, from_language=l1, to_language=l2, host='https://translate.google.com')
            chat.send_text(text)
        return True
