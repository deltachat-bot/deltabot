# -*- coding: utf-8 -*-
import urllib.request

from simplebot import Plugin


class Wttrin(Plugin):

    name = 'Wttr.in'
    description = 'Provides the !wttr <place> command to get weather info. Ex. !wttr La Havana, Cuba.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!wttr', msg.text)
        if arg is not None:
            resp = urllib.request.urlopen('http://wttr.in/%s?format=4' % arg)
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(resp.read().decode())
            return True
        return False
