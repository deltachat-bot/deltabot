# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin, PluginCommand


class Echo(Plugin):

    name = 'Echo'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_echo', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Simple plugin to echo back a message.')
        cls.long_description = _(
            'To use it you can simply send a message starting with the command /echo. For example:\n/echo hello world')
        cls.commands = [
            PluginCommand('/echo', ['[text]'], _('Echoes back the given text'), cls.on_echo)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def on_echo(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if not ctx.text:
            chat.send_text('🤖')
        else:
            chat.send_text(ctx.text)
