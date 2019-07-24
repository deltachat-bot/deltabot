# -*- coding: utf-8 -*-
import gettext
import os
import random

from simplebot import Plugin
import wikiquote as wq

class Wikiquote(Plugin):

    name = 'Wikiquote'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!quote'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale in wq.supported_languages():
            cls.LANG = ctx.locale
        else:
            cls.LANG = None
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_wikiquote', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_wikiquote', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin.description')
        cls.long_description = _('plugin.long_description')

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!quote', msg.text)
        if arg is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if cls.get_args('!today', arg):
            quote, author = wq.quote_of_the_day(lang=cls.LANG)
            quote = '"{}"\n\n― {}'.format(quote, author)
            chat.send_text(quote)
        elif arg:
            pages = wq.search(arg, lang=cls.LANG)
            if pages:
                author = pages[0]
                quote = '"%s"\n\n― %s' % (random.choice(wq.quotes(author, max_quotes=40, lang=cls.LANG)), author)
            else:
                quote = _('quote_not_found').format(arg)
            chat.send_text(quote)
        else:
            chat.send_text(cls.description+'\n\n'+cls.long_description)
        return True
        
