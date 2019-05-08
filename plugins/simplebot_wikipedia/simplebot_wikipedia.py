from simplebot import Plugin


class Wikipedia(Plugin):

    name = 'Wikipedia'
    description = 'Provides the !wiki <text> command to search <text> in Wikipedia'
    version = '0.1.0'
    author = 'sylar'
    
    def process(self, msg):
        arg = self.get_args('!wiki', msg.text)
        if arg is not None:
            chat = self.acc.create_chat_by_message(msg)
            chat.send_text('')
            return True
        return False
