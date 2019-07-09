# -*- coding: utf-8 -*-
from simplebot import Plugin
import wikipedia
from jinja2 import Environment, PackageLoader, select_autoescape


class Wikipedia(Plugin):

    name = 'Wikipedia'
    description = 'Provides the !w <text> command.'
    long_description = 'To search <text> in Wikipedia. Ex. !w GNU.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!w'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        if ctx.locale == 'es':
            cls.description = 'Provee el comando `!w <texto>` para buscar un artículo en la wikipedia. Ej. !w Cuba.'
            cls.PAGE_NOT_FOUND = 'Página no encontrada.'
        else:
            cls.PAGE_NOT_FOUND = 'Page not found.'
        wikipedia.set_lang(ctx.locale)
        
            

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!w', msg.text)
        if arg is not None:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            if not arg:
                template = cls.env.get_template('index.html')
                with open(cls.TEMP_FILE, 'w') as fd:
                    fd.write(template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
                chat.send_file(cls.TEMP_FILE, mime_type='text/html')
            else:
                if cls.get_args('!r', arg) is not None:
                    arg = wikipedia.random()
                try:
                    text = wikipedia.summary(arg)
                except wikipedia.exceptions.DisambiguationError as ex:
                    text = '\n'.join(ex.options)
                except wikipedia.PageError:
                    text = cls.PAGE_NOT_FOUND
                chat.send_text(arg+':\n\n'+text)
            return True
        return False
