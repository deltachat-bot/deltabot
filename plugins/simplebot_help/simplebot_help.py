from simplebot import Plugin
import pkg_resources


class Helper(Plugin):

    name = 'Help'
    description = 'Provides the !help command'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    
    def get_help(self):
        text = 'SimpleBot for Delta Chat.\nInstalled plugins:\n\n'
        for ep in pkg_resources.iter_entry_points('simplebot.plugins'):
            plugin = ep.load()
            text += '{}: {}\n\n'.format(plugin.name, plugin.description)
        return text

    def process(self, msg):
        if self.get_args('!help', msg.text) is not None:
            chat = self.acc.create_chat_by_message(msg)
            chat.send_text(self.get_help())
            return True
        return False
