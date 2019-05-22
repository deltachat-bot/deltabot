# -*- coding: utf-8 -*-
from simplebot import Plugin


class Echo(Plugin):

    name = 'Echo'
    description = 'Provides the !echo <text> command to reply back <text>. Ex. !echo hello world.'
    version = '0.1.1'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!echo <texto>` el cual hace que el bot responda el texto que le pases. Ej. !echo hola mundo.'

    @classmethod
    def process(cls, msg):
        text = cls.get_args('!echo', msg.text)
        if text is None:
            return False
        if not text:
            text = '🤖'
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True
