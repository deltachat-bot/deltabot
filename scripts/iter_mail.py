#!/usr/bin/env python
from __future__ import print_function
import sys
import os
import six
import datetime
import click
click.disable_unicode_literals_warning = True
import email.utils
import py

from deltabot.parse import render_hop_trace, parse_unaware_datetime_from_datestring


@click.command()
@click.argument("emailfile", required=True)
def main(emailfile):
    """iterate over maildirs and call functions for testing purposes. """
    if os.path.isdir(emailfile):
        for x in py.path.local(emailfile).visit(fil=py.path.local.isfile):
            process_one_message(x.strpath)
    elif os.path.isfile(emailfile):
        process_one_message (emailfile)



def process_one_message(fn):
    with open(fn, "rb") as fp:
        mime_msg = email.message_from_binary_file(fp)

    print ("** {}".format(mime_msg.get("Message-Id")))
    try:
        time_sent = parse_unaware_datetime_from_datestring(mime_msg.get("Date"))
    except Exception:
        return
    time_received = datetime.datetime.utcnow()  # fake
    for line in render_hop_trace(mime_msg, time_sent, time_received):
        print ("  " + line)


if __name__ == "__main__":
    main()
