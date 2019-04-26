class Runner:

    def __init__(self, acc):
        self.acc = acc

    def maybe_reply_to_message(self, msgid):
        msg = self.acc.get_message_by_id(int(msgid))
        sender_contact = msg.get_sender_contact()
        if sender_contact != self.acc.get_self_contact():
            print ("** creating/getting chat with incoming msg", msg)
            chat = self.acc.create_chat_by_message(msg)
            from_addr = sender_contact.addr
            mime_msg = msg.get_mime_headers()
            perf_lines = render_hop_trace(mime_msg, msg.time_sent, msg.time_received)
            rtext = "\n".join(("---> " + x) for x in msg.text.splitlines())
            chat.send_text(u"saw from {} viewtype {!r} fn={}: \n{}\nhop-trace:\n{}".format(
                           from_addr, msg.view_type.name, msg.basename, rtext, "\n".join(perf_lines)))
        self.acc.mark_seen_messages([msg])

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

    def serve(self):
        print("start serve")
        while 1:
            # self.dump_chats()
            # wait for incoming messages
            # DC_EVENT_MSGS_CHANGED for unknown contacts
            # DC_EVENT_INCOMING_MSG for known contacts
            in_events = "DC_EVENT_MSGS_CHANGED|DC_EVENT_INCOMING_MSG"
            ev = self.acc._evlogger.get_matching(in_events)
            if ev[2] == 0:
                print (ev)
                continue
            self.maybe_reply_to_message(msgid=ev[2])
