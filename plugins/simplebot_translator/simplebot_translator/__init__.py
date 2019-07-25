# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin
import translators as ts


class Translator(Plugin):

    name = 'Translator'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!tr'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_translator', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_translator', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin-description')
        cls.long_description = _('plugin-long-description')
    

    @classmethod
    def process(cls, msg):
        arg = cls.get_args(cls.cmd, msg.text)
        if arg is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if not arg:
            chat.send_text(cls.description+'\n\n'+cls.long_description)
        else:
            text = arg.split()
            l1, l2, text = text[0], text[1], ' '.join(text[2:])
            text = ts.google(text=text, from_language=l1, to_language=l2, host='https://translate.google.com')
            chat.send_text(text)
        return True
