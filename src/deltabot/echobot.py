from .botbase import BotBase
from .parse import render_hop_trace

class Runner(BotBase):

    # DC_EVENT_MSGS_CHANGED for unknown contacts
    # DC_EVENT_INCOMING_MSG for known contacts
    in_events = "DC_EVENT_MSGS_CHANGED|DC_EVENT_INCOMING_MSG"

    def prepare_reply(self, msg, chat):
        perf_lines = render_hop_trace(msg.mime_msg, msg.time_sent, msg.time_received)
        rtext = "\n".join(("---> " + x) for x in msg.lines)
        chat.set_reply_text(u"saw from {} viewtype {!r} fn={}: \n{}\nhop-trace:\n{}".format(
                            msg.from_addr,
                            msg.msg.view_type.name,
                            msg.msg.basename, rtext, "\n".join(perf_lines)))
