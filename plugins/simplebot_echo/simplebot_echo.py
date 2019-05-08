from simplebot import Plugin


class Echo(Plugin):

    name = 'Echo'
    description = 'Provides the !echo <text> command to reply back <text>'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    
    def process(self, msg):
        arg = self.get_args('!echo', msg.text)
        if arg is not None:
            chat = self.acc.create_chat_by_message(msg)
            chat.send_text(arg)
            return True
        return False
