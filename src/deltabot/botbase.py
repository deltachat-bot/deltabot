class BotBase:

    in_events = ()

    def __init__(self, acc, debug=False):
        self.acc = acc
        self.debug = debug

    def filter_events(self):
        ev = self.acc._evlogger.get_matching(self.in_events)
        return ev

    def run(self):
        print("start run")
        while 1:
            if self.debug:
                self.dump_chats()

            # wait for incoming messages
            ev = self.filter_events()
            if ev[2] == 0:
                print(ev)
                continue
            self.maybe_reply_to_message(msgid=ev[2])

    def maybe_reply_to_message(self, msgid):
        pass

    # debug

    def dump_chats(self):
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

