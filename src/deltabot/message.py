def get_message_by_id(acc, msgid):
    _msg = acc.get_message_by_id(int(msgid))
    return Message(_msg)


class Message:

    def __init__(self, msg):
        self.msg = msg

    @property
    def sender_contact(self):
        return self.msg.get_sender_contact()

    @property
    def from_addr(self):
        return self.sender_contact.addr

    @property
    def mime_msg(self):
        return self.msg.get_mime_headers()

    @property
    def time_sent(self):
        return self.msg.time_sent

    @property
    def time_received(self):
        return self.msg.time_received

    @property
    def lines(self):
        return self.msg.text.splitlines()
