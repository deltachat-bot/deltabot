import re
import time
import attr
from attr import validators as v
from email.utils import parsedate_to_datetime
from datetime import datetime


def parse_received_value(val):
    host = ""
    m = re.search("by (\S+)", val)
    if m:
        host = m.groups()[0]
    datestring = val.rsplit(";", 1)[-1].strip()
    dt = parsedate_to_datetime(datestring)
    return ParsedReceivedValue(val, host, datestring, dt)


def parse_date_to_float(date):
    try:
        return time.mktime(email.utils.parsedate(date))
    except TypeError:
        return 0.0


@attr.s
class ParsedReceivedValue(object):
    value = attr.ib(validator=v.instance_of(str))
    host = attr.ib(validator=v.instance_of(str))
    datestring = attr.ib(validator=v.instance_of(str))
    datetime = attr.ib(validator=v.instance_of(datetime))

