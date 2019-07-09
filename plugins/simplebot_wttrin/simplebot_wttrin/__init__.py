# -*- coding: utf-8 -*-
from urllib.error import HTTPError
from  urllib.parse import quote_plus
from  urllib.request import urlopen
from simplebot import Plugin


class Wttrin(Plugin):

    name = 'Wttr.in'
    description = 'Provides the !wttr <place> command.'
    long_description = 'To get weather info. Ex. !wttr La Havana, Cuba.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!wttr'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!wttr <lugar>` para optener el reporte del tiempo para el lugar dado. Ej. !wttr La Habana, Cuba.'
            
    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!wttr', msg.text)
        if arg is None:
            return False
        if arg:
            try:
                resp = urlopen('http://wttr.in/%s?format=4' % quote_plus(arg))
                text = resp.read().decode()
            except Exception as ex:
                cls.ctx.logger.exception(ex)
                text = str(ex)
        else:
            text = cls.description + cls.long_description
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True
