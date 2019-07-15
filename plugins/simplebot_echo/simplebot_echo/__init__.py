# -*- coding: utf-8 -*-
import os

from simplebot import Plugin


class Echo(Plugin):

    name = 'Echo'
    description = 'Simple plugin to reply back a message.'
    long_description = 'To use it you can simply send a message starting with the command !echo. For example:\n!echo hello world'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!echo'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        # if ctx.locale == 'es':
        #     cls.description = 'Un plugin sencillo para que el bot repita lo que envíes como un eco.'
        #     cls.long_description = 'Para usarlo puedes enviar un mensaje que comience con !echo, por ejemplo: !echo hola mundo y el bot responderá "hola mundo", esto permite comprobar de forma rápida que el bot está funcionando.'

    @classmethod
    def process(cls, msg):
        text = cls.get_args(cls.cmd, msg.text)
        if text is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if not text:
            chat.send_text(cls.description+'\n\n'+cls.long_description)
        else:
            chat.send_text(text)
        return True
