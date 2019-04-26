from .parse import render_hop_trace
from .botbase import BotBase

class Runner(BotBase):

    # DC_EVENT_MSGS_CHANGED for unknown contacts
    # DC_EVENT_INCOMING_MSG for known contacts
    in_events = "DC_EVENT_MSGS_CHANGED|DC_EVENT_INCOMING_MSG"

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

