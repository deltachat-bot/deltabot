
import os
import logging
from email.utils import parseaddr
from queue import Queue

import pytest

from deltachat.message import Message
from deltachat import account_hookimpl

from .cmdline import make_logger
from .bot import DeltaBot


@pytest.fixture
def mock_bot(acfactory, request):
    account = acfactory.get_configured_offline_account()
    return make_bot(account, request.module)


def make_bot(account, plugin_module):
    basedir = os.path.dirname(account.db_path)
    logger = make_logger(basedir, logging.DEBUG)
    bot = DeltaBot(account, logger)
    if not plugin_module.__name__.startswith("deltabot.builtin."):
        bot.plugins.add_module(plugin_module.__name__, plugin_module)
    return bot


@pytest.fixture
def mocker(mock_bot):
    class Mocker:
        def __init__(self):
            self.bot = mock_bot
            self.account = mock_bot.account

        def make_incoming_message(self, text, addr="Alice <alice@example.org>"):
            msg = Message.new_empty(self.account, "text")
            msg.set_text(text)
            name, routeable_addr = parseaddr(addr)
            contact = self.account.create_contact(email=routeable_addr, name=name)
            chat = self.account.create_chat_by_contact(contact)
            msg_in = chat.prepare_message(msg)
            return msg_in

        def run_command(self, text):
            msg = self.make_incoming_message(text)
            reply = self.bot.commands.deltabot_incoming_message(message=msg)
            return reply

    return Mocker()


@pytest.fixture
def bot_tester(acfactory, request):
    ac1, ac2 = acfactory.get_two_online_accounts()
    bot = make_bot(ac2, request.module)
    return BotTester(ac1, bot)


class BotTester:
    def __init__(self, send_account, bot):
        self.send_account = send_account
        self.send_account.set_config("displayname", "bot-tester")
        self.own_addr = self.send_account.get_config("addr")
        self.own_displayname = self.send_account.get_config("displayname")

        self.send_account.add_account_plugin(self)
        self.bot = bot
        bot_addr = bot.account.get_config("addr")
        self.bot_contact = self.send_account.create_contact(bot_addr)
        self.bot_chat = self.send_account.create_chat_by_contact(self.bot_contact)
        self._replies = Queue()

    @account_hookimpl
    def ac_incoming_message(self, message):
        if message.chat == self.bot_chat:
            self._replies.put(message)

    def send_command(self, text):
        self.bot_chat.send_text(text)
        return self._replies.get(timeout=5)
