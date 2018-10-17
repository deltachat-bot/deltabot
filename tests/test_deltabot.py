import email.parser
import pytest
from deltabot.parse import parse_received_value, render_hop_trace, parse_unaware_datetime_from_datestring
import datetime


def test_help(cmd):
    cmd.run_ok([], """
        *bot management*
        *init*
        *serve*
    """)


def test_parse_received_lines():
    s = """\
Received: by mail.merlinux.eu (Postfix, from userid 113)
        id 760591009CD; Sat, 13 Oct 2018 12:53:21 +0000 (UTC)
Received: from [127.0.0.1] (localhost [127.0.0.1])
        (using TLSv1.2 with cipher ECDHE-RSA-AES128-GCM-SHA256 (128/128 bits))
        (No client certificate requested)
        by mail.merlinux.eu (Postfix) with ESMTPS id 0049D1008EB
        for <holger@merlinux.eu>; Sat, 13 Oct 2018 12:53:20 +0000 (UTC)
Received: by mail-io1-xd45.google.com with SMTP id k9-v6sf13835663iob.16
        for <holger@merlinux.eu>; Sat, 13 Oct 2018 05:53:20 -0700 (PDT)
"""
    m = email.parser.Parser().parsestr(s)
    l = [parse_received_value(x) for x in m.get_all("Received")]
    assert len(l) == 3
    assert l[0].host == "mail.merlinux.eu"
    assert l[0].datestring == "Sat, 13 Oct 2018 12:53:21 +0000 (UTC)"
    assert l[0].datetime == datetime.datetime(2018, 10, 13, 12, 53, 21)

    assert l[1].host == "mail.merlinux.eu"
    assert l[1].datestring == "Sat, 13 Oct 2018 12:53:20 +0000 (UTC)"
    assert l[1].datetime == datetime.datetime(2018, 10, 13, 12, 53, 20)

    assert l[2].host == "mail-io1-xd45.google.com"
    assert l[2].datestring == "Sat, 13 Oct 2018 05:53:20 -0700 (PDT)"
    assert l[2].datetime == datetime.datetime(2018, 10, 13, 12, 53, 20)

    assert (l[0].datetime - l[2].datetime).total_seconds() == 1.0


def test_render_hoptrace():
    s = """\
Received: by mail.merlinux.eu (Postfix, from userid 113)
        id 760591009CD; Sat, 13 Oct 2018 12:53:21 +0000 (UTC)
Received: from [127.0.0.1] (localhost [127.0.0.1])
        (using TLSv1.2 with cipher ECDHE-RSA-AES128-GCM-SHA256 (128/128 bits))
        (No client certificate requested)
        by mail.merlinux.eu (Postfix) with ESMTPS id 0049D1008EB
        for <holger@merlinux.eu>; Sat, 13 Oct 2018 12:53:20 +0000 (UTC)
Received: by mail-io1-xd45.google.com with SMTP id k9-v6sf13835663iob.16
        for <holger@merlinux.eu>; Sat, 13 Oct 2018 05:53:20 -0700 (PDT)
"""
    time_sent = parse_unaware_datetime_from_datestring("Sat, 13 Oct 2018 05:52:20 -0700 (PDT)")
    time_received = datetime.datetime.utcnow()
    m = email.parser.Parser().parsestr(s)
    render_hop_trace(m, time_sent, time_received)
