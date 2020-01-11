# -*- coding: utf-8 -*-
from urllib.parse import quote_plus
import gettext
import os

from simplebot import Plugin, PluginCommand
import bs4
import requests


HEADERS = {
    'user-agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/60.0'}


class Avatar(Plugin):

    name = 'Avatar'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_avatar', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Generate avatars.')
        cls.long_description = _(
            'Uses: https://www.peppercarrot.com/extras/html/2016_cat-generator')
        cls.commands = [
            PluginCommand('/avatar', ['[text]'], _(
                'Generates a cat avatar based on the given text, if no text is given a random avatar is generated'), cls.avatar_cmd),
            PluginCommand('/avatar/bird', ['[text]'], _('Generates a bird avatar based on the given text, if no text is given a random avatar is generated'), cls.bird_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def avatar_cmd(cls, ctx):
        cls._avatar_cmd(
            ctx, 'https://www.peppercarrot.com/extras/html/2016_cat-generator/')

    @classmethod
    def bird_cmd(cls, ctx):
        cls._avatar_cmd(
            ctx, 'https://www.peppercarrot.com/extras/html/2019_bird-generator/')

    @classmethod
    def _avatar_cmd(cls, ctx, url):
        chat = cls.bot.get_chat(ctx.msg)

        if not ctx.text:
            with requests.get(url, headers=HEADERS) as r:
                r.raise_for_status()
                soup = bs4.BeautifulSoup(r.text, 'html.parser')
            ctx.text = soup.find('img', class_='avatar')[
                'src'].rsplit('=', maxsplit=1)[-1]

        url += 'avatar.php?seed=' + quote_plus(ctx.text)
        with requests.get(url, headers=HEADERS) as r:
            r.raise_for_status()
            fpath = cls.bot.get_blobpath('avatar.png')
            with open(fpath, 'wb') as fd:
                fd.write(r.content)
        cls.bot.send_file(chat, fpath, ctx.text, 'image')
