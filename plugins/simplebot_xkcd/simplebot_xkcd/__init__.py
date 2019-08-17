# -*- coding: utf-8 -*-
import gettext
import os

from simplebot import Plugin
import xkcd


class XKCD(Plugin):

    name = 'xkcd'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)
        cls.blobsdir = os.path.join(cls.bot.basedir, 'account.db-blobs')

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_xkcd', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('See xkcd.com comics in Delta Chat.')
        cls.commands = [
            ('/xkcd', ['[num]'], _('Sends the comic with the give number or a ramdom comic if no number is provided.'), cls.xkcd_cmd),
            ('/xkcd/l', [], _('Sends the latest comic released in xkcd.'), cls.latest_cmd), ]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def xkcd_cmd(cls, msg, num):
        comic = xkcd.getComic(int(num)) if num else xkcd.getRandomComic()
        cls.bot.get_chat(msg).send_image(comic.download(cls.blobsdir))

    @classmethod
    def latest_cmd(cls, msg, args):
        comic = xkcd.getLatestComic()
        cls.bot.get_chat(msg).send_image(comic.download(cls.blobsdir))
