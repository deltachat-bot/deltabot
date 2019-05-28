# -*- coding: utf-8 -*-
import os

from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape


class Echo(Plugin):

    name = 'Echo'
    description = 'Simple plugin to reply back a message.'
    long_description = 'To use it you can simply send a message starting with the command !echo. For example: !echo hello world'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!echo'

    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.template = env.get_template('index.html')
        if ctx.locale == 'es':
            cls.description = 'Un plugin sencillo para que el bot repita lo que envíes como un eco.'
            cls.long_description = 'Para usarlo puedes enviar un mensaje que comience con !echo, por ejemplo: !echo hola mundo y el bot responderá "hola mundo", esto permite comprobar de forma rápida que el bot está funcionando.'
            cls.NOSCRIPT = 'Necesitas un navegador que soporte JavaScript para poder usar esta funcionalidad.'

    @classmethod
    def process(cls, msg):
        text = cls.get_args(cls.cmd, msg.text)
        if text is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if not text:
            with open(cls.TEMP_FILE, 'w') as fd:
                fd.write(cls.template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
            chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        else:
            chat.send_text(text)
        return True
