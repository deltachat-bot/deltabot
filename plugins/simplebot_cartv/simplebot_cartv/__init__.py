# -*- coding: utf-8 -*-
from datetime import datetime
import gettext
import html
import os

from simplebot import Plugin, PluginCommand
import pytz
import requests


url = "http://www.tvcubana.icrt.cu/cartv/cartv-core/app.php?action=dia&canal={0}&fecha={1}"

tv_emoji = '📺'
cal_emoji = '📆'
aster_emoji = '✳'

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


class CarTV(Plugin):

    name = 'Cartelera TV'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_cartv', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = 'Muestra la cartelera de la TV cubana'
        cls.long_description = 'Por ejemplo: /cartv Cubavision\n/cartv para mostrar todos los canales'
        cls.commands = [
            PluginCommand('/cartv', ['[canal]'], 'Mostrar cartelera para el canal dado', cls.cartv_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def cartv_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        eastern = pytz.timezone("US/Eastern")
        today = datetime.now(eastern).strftime('%d-%m-%Y')

        if ctx.text:
            if ctx.text not in channels:
                chat.send_text(
                    'El canal puede ser:\n{}'.format('\n'.join(channels)))
                return
            chans = [ctx.text]
        else:
            chans = channels

        text = ''
        for chan in chans:
            with requests.get(url.format(chan, today)) as req:
                req.raise_for_status()
                text += cls.format_channel(req.text)
            text += '\n\n'
        chat.send_text(text)

    @classmethod
    def format_channel(cls, text):
        lines = html.unescape(text).splitlines()
        lines = [l.strip().replace('\t', ' ') for l in lines]

        text = '{} {}\n'.format(tv_emoji, lines[0])
        text += '{} {}\n'.format(cal_emoji, lines[1])

        for l in lines[2:]:
            text += '{} {}\n'.format(aster_emoji, l)

        return text
