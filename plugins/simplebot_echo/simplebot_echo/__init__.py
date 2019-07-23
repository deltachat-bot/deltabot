# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin


class Echo(Plugin):

    name = 'Echo'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!echo'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_echo', localedir=localedir,
                                   languages=[ctx.locale], fallback=True)
        lang.install()
        
        cls.description = _('Simple plugin to echo back a message.')
        cls.long_description = _('To use it you can simply send a message starting with the command !echo. For example:\n!echo hello world')
    
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
