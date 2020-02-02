# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin, Mode, PluginCommand
from jinja2 import Environment, PackageLoader, select_autoescape


class Helper(Plugin):

    name = 'Help'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.template = env.get_template('index.html')
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_help', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Provides help.')
        cls.commands = [PluginCommand(
            '/help', [], _('Will send you a list of installed plugins and their help.'), cls.help_cmd)]
        cls.bot.add_commands(cls.commands)
        cls.bot.add_on_cmd_processed_listener(cls.on_cmd_processed)
        cls.bot.add_on_msg_processed_listener(cls.on_msg_processed)

        cls.MORE = _('More')
        cls.LESS = _('Less')

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.bot.remove_on_cmd_processed_listener(cls.on_cmd_processed)
        cls.bot.remove_on_msg_processed_listener(cls.on_msg_processed)

    @classmethod
    def help_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
            text = _('Commands:\n\n')
            for c in cls.bot.commands:
                text += '{0} {1}\n{2}\n\n'.format(
                    c.cmd, ' '.join(c.args), c.description)
            chat.send_text(text)
        else:
            plugins = sorted(cls.bot.plugins, key=lambda p: p.name)
            plugins.remove(cls)
            plugins.insert(0, cls)
            bot_addr = cls.bot.get_address()
            html = cls.template.render(
                plugin=cls, plugins=plugins, bot_addr=bot_addr)
            cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)

    @classmethod
    def on_cmd_processed(cls, ctx):
        if not ctx.processed:
            cls.bot.get_chat(ctx.msg).send_text(
                _('Unknow command. Please send /help to learn how to use me.'))

    @classmethod
    def on_msg_processed(cls, ctx):
        if not cls.bot.is_group(cls.bot.get_chat(ctx.msg)):
            cls.on_cmd_processed(ctx)
