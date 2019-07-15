# -*- coding: utf-8 -*-
import os
import random

from simplebot import Plugin
import wikiquote as wq

class Wikiquote(Plugin):

    name = 'Wikiquote'
    description = 'Provides the !quote [text] command.'
    long_description = 'To get the quote of the day or a random quote from the given text.\nExamples:\n!quote!today\n!quote Richard Stallman'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!quote'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando `!quote [texto]` para mostrar una frase aleatoria del alguna persona relacionada con el texto dado, o la frase del día si no le pasas ningún texto. Ej. !quote José Martí'
        #     cls.QUOTE_NOT_FOUND = 'No se encontó ninguna frase para: "%s"'
        # else:
        #     cls.QUOTE_NOT_FOUND = 'No quote found for: "%s"'
        if ctx.locale in wq.supported_languages():
            cls.LANG = ctx.locale
        else:
            cls.LANG = None

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
                quote = cls.QUOTE_NOT_FOUND % arg
            chat.send_text(quote)
        else:
            chat.send_text(cls.description+'\n\n'+cls.long_description)
        return True
        
