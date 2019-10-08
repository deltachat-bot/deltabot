# -*- coding: utf-8 -*-
import gettext
import os
import random

from simplebot import Plugin, PluginCommand
import wikiquote as wq


class Wikiquote(Plugin):

    name = 'Wikiquote'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_wikiquote', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()
        cls.description = _('Access Wikiquote content on Delta Chat.')
        cls.commands = [
            PluginCommand('/quote', ['[text]'], _('Search in Wikiquote or get the quote of the day if no text is given.'), cls.quote_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def quote_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if ctx.locale in wq.supported_languages():
            lang = ctx.locale
        else:
            lang = None
        if ctx.text:
            pages = wq.search(ctx.text, lang=lang)
            if pages:
                author = pages[0]
                quote = '"{}"\n\n― {}'.format(random.choice(
                    wq.quotes(author, max_quotes=100, lang=lang)), author)
            else:
                quote = _('No quote found for: {}').format(ctx.text)
            chat.send_text(quote)
        else:
            quote, author = wq.quote_of_the_day(lang=lang)
            quote = '"{}"\n\n― {}'.format(quote, author)
            chat.send_text(quote)
