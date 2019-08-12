# -*- coding: utf-8 -*-
import gettext
import os
import random

from simplebot import Plugin
import wikiquote as wq


class Wikiquote(Plugin):

    name = 'Wikiquote'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        if bot.locale in wq.supported_languages():
            cls.LANG = bot.locale
        else:
            cls.LANG = None
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_wikiquote', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()
        cls.description = _('Access Wikiquote content on Delta Chat.')
        cls.commands = [('/quote', ['[text]'], _(
            'Search in Wikiquote or get the quote of the day if no text is given.'), cls.quote_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def quote_cmd(cls, msg, text):
        chat = cls.bot.get_chat(msg)
        if text:
            pages = wq.search(text, lang=cls.LANG)
            if pages:
                author = pages[0]
                quote = '"%s"\n\n― %s' % (random.choice(
                    wq.quotes(author, max_quotes=100, lang=cls.LANG)), author)
            else:
                quote = _('No quote found for: {}').format(text)
            chat.send_text(quote)
        else:
            quote, author = wq.quote_of_the_day(lang=cls.LANG)
            quote = '"{}"\n\n― {}'.format(quote, author)
            chat.send_text(quote)
