# -*- coding: utf-8 -*-
import gettext
import os
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_configure(bot):
    localedir = os.path.join(os.path.dirname(__file__), 'locale')
    lang = gettext.translation('deltabot_echo', localedir=localedir,
                               languages=[bot.locale], fallback=True)
    _ = lang.gettext

    bot.register_command(
        name="/echo",
        description=_('Echoes back the given text.'),
        long_description= _(
            'To use it you can simply send a message starting with '
            'the command /echo. For example:\n/echo hello world'),
        func=process_command_echo
    )


def process_command_echo(command):
    text = command.payload
    if not text:
        message = command.message
        f = message.get_mime_headers()['from']
        name = message.get_sender_contact().display_name
        text = 'From: {}\nDisplay Name: {}'.format(f, name)
    command.message.chat.send_text(text)

