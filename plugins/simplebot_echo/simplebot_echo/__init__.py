# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin


class Echo(Plugin):

    name = 'Echo'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        cls.bot = bot
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_echo', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()
        cls.description = _('Simple plugin to echo back a message.')
        cls.long_description = _(
            'To use it you can simply send a message starting with the command /echo. For example:\n/echo hello world')
        cls.commands = [
            ('/echo', ['[text]'], _('Echoes back the given text'), cls.on_echo)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def on_echo(cls, msg, text):
        chat = cls.bot.get_chat(msg)
        if not text:
            chat.send_text('🤖')
        else:
            chat.send_text(text)
