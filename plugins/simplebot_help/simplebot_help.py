# -*- coding: utf-8 -*-
from simplebot import Plugin


class Helper(Plugin):

    name = 'Help'
    description = 'Provides the !help command. Ex. !help.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    BANNER = 'SimpleBot for Delta Chat.\nInstalled plugins:\n\n'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando !help que muestra este mensaje. Ej. !help.'
            cls.BANNER = 'SimpleBot para Delta Chat.\nPlugins instalados:\n\n'

    @classmethod
    def process(cls, msg):
        if cls.get_args('!help', msg.text) is not None:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            text = cls.BANNER
            for p in cls.ctx.plugins:
                text += '📀 {}:\n{}\n\n'.format(p.name, p.description)
            chat.send_text(text)
            return True
        return False
