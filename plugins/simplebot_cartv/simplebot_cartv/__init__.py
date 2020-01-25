# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin, PluginCommand

import requests
import html
from datetime import date

url = "http://www.tvcubana.icrt.cu/cartv/cartv-core/app.php?action=dia&canal={0}&fecha={1}"

tv_emoji = '📺'
cal_emoji = '📆'
aster_emoji = '✳️'

channels = [
    'Cubavision',
    'Telerebelde',
    'Educativo',
    'Educativo 2',
    'Multivision',
    'Canal Clave',
    'Caribe',
    'Habana'
]

class Cartv(Plugin):

    name = 'Cartv'
    version = '0.3.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_cartv', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Mostrar cartelera de la television cubana')
        cls.long_description = _(
            '/cartv <channel> ej: /cartv Cubavision o /cartv para mostrar todos los canales')
        cls.commands = [
            PluginCommand('/cartv', ['[text]'], _('Mostrar cartelera para el canal <text> ej: /cartv Cubavision'), cls.cartv_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def cartv_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        today = date.today().strftime('%d-%m-%Y')

        if not ctx.text:
            for channel in channels:
                res = requests.get(url.format(channel, today))
                res.raise_for_status()
                msg = cls.parser(res.text)
                chat.send_text(msg)
        else:
            res = requests.get(url.format(ctx.text, today))
            res.raise_for_status()
            msg = cls.parser(res.text)
            chat.send_text(msg)

    @classmethod
    def parser(cls, ogly_text):
        lines = html.unescape(ogly_text).split('\n')

        beuty_text = tv_emoji + ' ' + lines[0] + '\n'
        beuty_text += cal_emoji + ' ' + lines[1] + '\n'

        for i in range(2, len(lines)):
            beuty_text += aster_emoji + ' ' + lines[i] + '\n'

        beuty_text = beuty_text.replace('\t', ' ')

        return beuty_text
