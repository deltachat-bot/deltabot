# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape


class Helper(Plugin):

    name = 'Help'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        cls.TEMP_FILE = os.path.join(cls.bot.basedir, cls.name)

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
        cls.commands = [
            ('/help', [], _('Will send you a list of installed plugins and their help.'), cls.help_cmd)]
        cls.bot.add_commands(cls.commands)
        cls.bot.add_on_cmd_processed_listener(cls.on_cmd_processed)
        cls.bot.add_on_msg_processed_listener(cls.on_msg_processed)

        cls.NOSCRIPT = _(
            'You need a browser with JavaScript support for this page to work correctly.')
        cls.MORE = _('More')
        cls.LESS = _('Less')
        cls.USE = _('Use')

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.bot.remove_on_cmd_processed_listener(cls.on_cmd_processed)
        cls.bot.remove_on_msg_processed_listener(cls.on_msg_processed)

    @classmethod
    def help_cmd(cls, msg, text):
        chat = cls.bot.get_chat(msg)
        cls.send_html_help(chat, msg.user_agent)

    @classmethod
    def on_cmd_processed(cls, msg, processed):
        chat = cls.bot.get_chat(msg)
        if not processed:
            chat.send_text(
                _('Unknow command. Please send /help to learn how to use me.'))

    @classmethod
    def on_msg_processed(cls, msg, processed):
        if not cls.bot.is_group(cls.bot.get_chat(msg)):
            cls.on_cmd_processed(msg, processed)

    @classmethod
    def send_html_help(cls, chat, user_agent):
        plugins = sorted(cls.bot.plugins, key=lambda p: p.name)
        plugins.remove(cls)
        plugins.insert(0, cls)
        bot_addr = cls.bot.get_address()
        html = cls.template.render(
            plugin=cls, plugins=plugins, bot_addr=bot_addr)
        cls.bot.send_html(chat, html, cls.TEMP_FILE, user_agent)
