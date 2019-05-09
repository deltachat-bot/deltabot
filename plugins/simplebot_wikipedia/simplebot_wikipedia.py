from simplebot import Plugin
import wikipedia


#wikipedia.set_lang('es')


class Wikipedia(Plugin):

    name = 'Wikipedia'
    description = 'Provides the !w <text> command to search <text> in Wikipedia. Ex. !w GNU.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!w', msg.text)
        if arg is not None:
            try:
                summary = wikipedia.summary(arg)
            except wikipedia.PageError:
                summary = 'Page not found.'
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(arg+':\n\n'+summary)
            return True
        return False
