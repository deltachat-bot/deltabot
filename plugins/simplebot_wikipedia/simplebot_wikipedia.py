from simplebot import Plugin

import wikipedia


class Wikipedia(Plugin):

    name = 'Wikipedia'
    description = 'Provides the !w <text> command to search <text> in Wikipedia'
    version = '0.1.0'
    author = 'adbenitez'
    #wikipedia.set_lang('es')
    
    def process(self, msg):
        arg = self.get_args('!w', msg.text)
        if arg is not None:
            try:
                summary = wikipedia.summary(arg)
            except wikipedia.PageError:
                summary = 'Not found.'
            chat = self.acc.create_chat_by_message(msg)
            chat.send_text(arg+':\n\n'+summary)
            return True
        return False
