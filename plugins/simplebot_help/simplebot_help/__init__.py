# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape


class Helper(Plugin):

    name = 'Help'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!help'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            #autoescape=select_autoescape(['html', 'xml'])
        )
        cls.template = env.get_template('index.html')
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_help', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_help', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin.description')
        cls.long_description = _('plugin.long_description')
        cls.NOSCRIPT = _('noscript_msg')
        cls.MORE = _('more_btn')
        cls.LESS = _('less_btn')
        cls.USE = _('use_btn')
    

    @classmethod
    def process(cls, msg):
        if cls.get_args(cls.cmd, msg.text) is not None:
            plugins = sorted(cls.ctx.plugins, key=lambda p: p.name)
            plugins.remove(cls)
            plugins.insert(0, cls)
            bot_addr = cls.ctx.acc.get_self_contact().addr
            html = cls.template.render(plugin=cls, plugins=plugins, bot_addr=bot_addr)
            with open(cls.TEMP_FILE, 'w') as fd:
                fd.write(html)
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_file(cls.TEMP_FILE, mime_type='text/html')
            return True
        return False
