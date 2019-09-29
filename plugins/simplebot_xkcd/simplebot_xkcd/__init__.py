# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin, PluginCommand
import xkcd


class XKCD(Plugin):

    name = 'xkcd'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_xkcd', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('See xkcd.com comics in Delta Chat.')
        cls.commands = [
            PluginCommand('/xkcd', ['[num]'], _(
                'Sends the comic with the give number or a ramdom comic if no number is provided.'), cls.xkcd_cmd),
            PluginCommand('/xkcd/l', [], _('Sends the latest comic released in xkcd.'), cls.latest_cmd), ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def xkcd_cmd(cls, ctx):
        comic = xkcd.getComic(
            int(ctx.text)) if ctx.text else xkcd.getRandomComic()
        cls.bot.get_chat(ctx.msg).send_image(
            comic.download(cls.bot.get_blobdir()))

    @classmethod
    def latest_cmd(cls, ctx):
        comic = xkcd.getLatestComic()
        cls.bot.get_chat(ctx.msg).send_image(
            comic.download(cls.bot.get_blobdir()))
