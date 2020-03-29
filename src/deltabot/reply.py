
from deltachat.message import Message


class TextReply:
    def __init__(self, incoming_message, text, terminal=False):
        self.incoming_message = incoming_message
        self.chat = self.incoming_message.chat
        self.msg = Message.new_empty(self.chat.account, "text")
        self.msg.set_text(text)
        self.terminal = terminal
