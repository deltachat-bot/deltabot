# -*- coding: utf-8 -*-
from urllib.parse import quote_plus
import gettext
import os

from simplebot import Plugin, PluginCommand
import bs4
import requests


HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}


class Meme(Plugin):

    name = 'Meme'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_meme', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Generate memes.')
        cls.long_description = _(
            'Uses: https://m.cuantarazon.com/aleatorio/')
        cls.commands = [
            PluginCommand('/meme', ['[text]'], _(
                'Generate a random meme'), cls.meme_cmd
            ),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def meme_cmd(cls, ctx):
        cls._meme_cmd(
            ctx, 'https://m.cuantarazon.com/aleatorio/')

    @classmethod
    def _meme_cmd(cls, ctx, url):
        chat = cls.bot.get_chat(ctx.msg)

        if not ctx.text:
            with requests.get(url, headers=HEADERS) as r:
                r.raise_for_status()
                soup = bs4.BeautifulSoup(r.text, 'html.parser')

            img_url = soup.find('div', class_='storyContent').find('img')['src'].split('?')[0]
            ctx.text = soup.find('div', class_='storyContent').find('img')['alt']

        with requests.get(img_url, headers=HEADERS) as r:
            r.raise_for_status()
            fpath = cls.bot.get_blobpath('meme.png')
            with open(fpath, 'wb') as fd:
                fd.write(r.content)
        cls.bot.send_file(chat, fpath, ctx.text, 'image')
