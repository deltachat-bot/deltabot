from simplebot import Plugin
import pkg_resources


class Helper(Plugin):

    name = 'Help'
    description = 'Provides the !help command. Ex. !help.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def process(cls, msg):
        if cls.get_args('!help', msg.text) is not None:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            text = 'SimpleBot for Delta Chat.\nInstalled plugins:\n\n'
            for p in cls.ctx.plugins:
                text += '📀 {}[{}]:\n{}\n\n'.format(p.name, p.version, p.description)
            chat.send_text(text)
            return True
        return False
