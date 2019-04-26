from .chat import create_chat_by_message
from .message import get_message_by_id 

class BotBase:

    in_events = ()
    cmd_handler = None

    def __init__(self, acc, debug=False):
        self.acc = acc
        self.debug = debug

    def prepare_reply(self, message, chat):
        """Every bot should implement this method"""
        pass

    def run(self):
        print("start run")
        while 1:
            if self.debug:
                self._dump_chats()

            # wait for incoming messages
            ev = self._filter_events()
            if ev[2] == 0:
                print(ev)
                continue
            self._maybe_reply_to_message(msgid=ev[2])

    def _filter_events(self):
        return self.acc._evlogger.get_matching(self.in_events)

    def _maybe_reply_to_message(self, msgid):
        msg = get_message_by_id(self.acc, int(msgid))
        if msg.sender_contact != self.acc.get_self_contact():
            if self.cmd_handler is not None:
                if self.cmd_handler.is_valid_cmd(msg):
                    self._process_reply(msg)
            else:
                self._process_reply(msg)
        self.acc.mark_seen_messages([msg.msg])

    def _process_reply(self, msg):
        print ("** creating/getting chat with incoming msg", msg)
        chat = create_chat_by_message(self.acc, msg)
        self.prepare_reply(msg, chat)
        chat.send_reply()

    # debug

    def _dump_chats(self):
        print("*" * 80)
        chatlist = self.acc.get_chats()
        for chat in chatlist:
            print ("chat id={}, name={}".format(chat.id, chat.get_name()))
            for sub in chat.get_contacts():
                print("  member:", sub.addr)
            for msg in chat.get_messages()[-10:]:
                print(u"  msg {}, from {}: {!r}".format(
                      msg.id,
                      msg.get_sender_contact().addr,
                      msg.text))
