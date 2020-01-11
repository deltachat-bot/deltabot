# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin, PluginCommand
from translators.google import LANGUAGES
import translators as ts


LANGUAGES = '\n'.join(['* {}: {}'.format(v, k)
                       for k, v in sorted(LANGUAGES.items(), key=lambda e: e[1])])


class Translator(Plugin):

    name = 'Translator'
    version = '0.4.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_translator', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()
        cls.description = _('Translate text. Example: /tr en es hello world')
        cls.commands = [
            PluginCommand('/tr', ['<lang1>', '<lang2>', '<text>'],
                          _('Translate text from lang1 to lang2'), cls.tr_cmd),
            PluginCommand('/tr/list', [], _('List supported languages and their code'), cls.list_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def tr_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if not ctx.text:
            chat.send_text(cls.description)
        else:
            l1, l2, text = ctx.text.split(maxsplit=2)
            chat.send_text(ts.google(text=text, from_language=l1,
                                     to_language=l2, host='https://translate.google.com'))

    @classmethod
    def list_cmd(cls, ctx):
        cls.bot.get_chat(ctx.msg).send_text(LANGUAGES)
