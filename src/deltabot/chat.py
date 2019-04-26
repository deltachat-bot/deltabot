def create_chat_by_message(acc, msg):
    chat = acc.create_chat_by_message(msg.msg)
    return Chat(chat)


class Chat:

    def __init__(self, chat):
        self.chat = chat
        self.reply_text = ""
    
    def set_reply_text(self, text):
        self.reply_text = text

    def send_reply(self):
        self.chat.send_text(self.reply_text)
