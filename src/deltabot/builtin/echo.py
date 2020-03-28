# -*- coding: utf-8 -*-
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_configure(bot):
    bot.commands.register(name="/echo", func=process_command_echo)


def process_command_echo(command):
    """ Echoes back received message.

    To use it you can simply send a message starting with
    the command '/echo'. Example: `/echo hello world`
    """
    text = command.payload
    if not text:
        message = command.message
        contact = message.get_sender_contact()
        text = 'From: {} <{}>'.format(contact.display_name, contact.addr)
    return text


def test_mock_echo(mocker):
    reply = mocker.run_command("/echo")
    assert reply.msg.text.startswith("From")
    assert mocker.run_command("/echo hello").msg.text == "hello"


def test_echo(bot_tester):
    msg_reply = bot_tester.send_command("/echo")
    assert msg_reply.text.startswith("From")
    assert bot_tester.own_addr in msg_reply.text
    assert bot_tester.own_displayname in msg_reply.text
