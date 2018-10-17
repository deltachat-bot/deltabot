import sys
import re
import time
import attr
from attr import validators as v
from email.utils import parsedate_to_datetime
from traceback import format_exc
from datetime import datetime


def render_hop_trace(mime_msg, time_sent, time_received):
    assert isinstance(time_sent, datetime), repr(time_sent)
    assert isinstance(time_received, datetime), repr(time_received)
    def elapsed(t):
        return (t - time_sent).total_seconds()

    l = ["device-received: {}".format(elapsed(time_received))]
    rcvd_headers = mime_msg.get_all("Received")
    if rcvd_headers:
        for val in rcvd_headers:
            try:
                rcvd = parse_received_value(val)
            except Exception:
                print(format_exc())
                print("could not parse {!r}".format(val))
                return l # break
            l.append("{}: {}s".format(rcvd.host, elapsed(rcvd.datetime)))
    l.append("device-sent: 0.0s ({})".format(time_sent.isoformat()))
    return l


def parse_received_value(val):
    host = ""
    m = re.search("by (\S+)", val)
    if m:
        host = m.groups()[0]
    datestring = val.rsplit(";", 1)[-1].strip()
    dt = parse_unaware_datetime_from_datestring(datestring)
    return ParsedReceivedValue(val, host, datestring, dt)


def parse_unaware_datetime_from_datestring(datestring):
    dt1 = parsedate_to_datetime(datestring)
    return datetime.utcfromtimestamp(dt1.timestamp())


@attr.s
class ParsedReceivedValue(object):
    value = attr.ib(validator=v.instance_of(str))
    host = attr.ib(validator=v.instance_of(str))
    datestring = attr.ib(validator=v.instance_of(str))
    datetime = attr.ib(validator=v.instance_of(datetime))




