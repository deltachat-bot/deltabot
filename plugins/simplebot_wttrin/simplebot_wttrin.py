# -*- coding: utf-8 -*-
from urllib.error import HTTPError
from  urllib.parse import quote_plus
from  urllib.request import urlopen
from simplebot import Plugin


class Wttrin(Plugin):

    name = 'Wttr.in'
    description = 'Provides the !wttr <place> command to get weather info. Ex. !wttr La Havana, Cuba.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!wttr <lugar>` para optener el reporte del tiempo para el lugar dado. Ej. !wttr La Habana, Cuba.'
            
    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!wttr', msg.text)
        if arg is not None:
            try:
                resp = urlopen('http://wttr.in/%s?format=4' % quote_plus(arg))
                text = resp.read().decode()
            except Exception as ex:
                cls.ctx.logger.exception(ex)
                text = str(ex)
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(text)
            return True
        return False
