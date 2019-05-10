# -*- coding: utf-8 -*-
from simplebot import Plugin


class Echo(Plugin):

    name = 'Echo'
    description = 'Provides the !echo <text> command to reply back <text>. Ex. !echo hello world.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!echo'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!echo <texto>` el cual hace que el bot responda el texto que le pases. Ej. !echo hola mundo.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args(cls.cmd, msg.text)
        if arg is not None:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(arg)
            return True
        return False
