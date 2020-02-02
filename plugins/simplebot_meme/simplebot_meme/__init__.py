# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin, PluginCommand
import bs4
import requests


HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}


class Meme(Plugin):

    name = 'Meme'
    version = '0.2.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_meme', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Retrieve memes.')
        cls.long_description = _(
            'Uses: https://m.cuantarazon.com')
        cls.commands = [
            PluginCommand('/meme', [], _(
                'Generate a random meme'), cls.meme_cmd
            ),
        ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def meme_cmd(cls, ctx):
        url = 'https://m.cuantarazon.com/aleatorio/'

        with requests.get(url, headers=HEADERS) as r:
            r.raise_for_status()
            soup = bs4.BeautifulSoup(r.text, 'html.parser')
        img = soup('div', class_='storyContent')[-1].img
        ctx.text = '{}\n\n{}'.format(img['alt'], img['src'])

        with requests.get(img['src'], headers=HEADERS) as r:
            r.raise_for_status()
            fpath = cls.bot.get_blobpath('meme.png')
            with open(fpath, 'wb') as fd:
                fd.write(r.content)

        chat = cls.bot.get_chat(ctx.msg)
        cls.bot.send_file(chat, fpath, ctx.text, 'image')
