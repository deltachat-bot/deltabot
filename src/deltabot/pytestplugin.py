
import os
import logging
from email.utils import parseaddr
from queue import Queue

import pytest
from _pytest.pytester import LineMatcher

from deltachat.message import Message
from deltachat import account_hookimpl

from .cmdline import make_logger, _get_click_group
from .plugins import make_plugin_manager
from .bot import DeltaBot, Replies


@pytest.fixture
def mock_bot(acfactory, request):
    account = acfactory.get_configured_offline_account()
    return make_bot(request, account, request.module)


def make_bot(request, account, plugin_module):
    basedir = os.path.dirname(account.db_path)

    # we use a new plugin manager for each test
    pm = make_plugin_manager()

    # initialize command line
    _ = _get_click_group(pm)

    logger = make_logger(basedir, logging.DEBUG)
    bot = DeltaBot(account, logger, plugin_manager=pm)

    # we auto-register the (non-builtin) module
    # which contains the test which requested this bot
    if not plugin_module.__name__.startswith("deltabot.builtin."):
        bot.plugins.add_module(plugin_module.__name__, plugin_module)

    # startup bot
    request.addfinalizer(bot.trigger_shutdown)
    bot.start()
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
            replies = Replies(self.account)
            self.bot.commands.deltabot_incoming_message(message=msg, replies=replies)
            l = list(replies.get_reply_messages())
            if not l:
                raise ValueError("no reply for command {!r}".format(text))
            if len(l) > 1:
                raise ValueError("more than one reply for {!r}".format(text))
            return l[0]

    return Mocker()


@pytest.fixture
def bot_tester(acfactory, request):
    ac1, ac2 = acfactory.get_two_online_accounts()
    bot = make_bot(request, ac2, request.module)
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
        return self._replies.get(timeout=30)


class ClickRunner:
    def __init__(self):
        self._rootargs = []

    def set_basedir(self, account_dir):
        self._rootargs.insert(0, "--basedir")
        self._rootargs.insert(1, account_dir)

    def invoke(self, args, input):
        from click.testing import CliRunner

        # create a new plugin manager for each command line invocation
        pm = make_plugin_manager()
        click_group = _get_click_group(pm)
        argv = self._rootargs + args
        return CliRunner().invoke(
            click_group, argv,
            catch_exceptions=False,
            input=input,
            obj=pm
        )

    def run_ok(self, args, fnl=None, input=None):
        __tracebackhide__ = True
        res = self.invoke(args, input)
        if res.exit_code != 0:
            print(res.output)
            raise Exception("cmd exited with %d: %s" % (res.exit_code, args))
        return _perform_match(res.output, fnl)

    def run_fail(self, args, fnl=None, input=None, code=None):
        __tracebackhide__ = True
        res = self.invoke(args, input)
        if res.exit_code == 0 or (code is not None and res.exit_code != code):
            print(res.output)
            raise Exception("got exit code {!r}, expected {!r}, output: {}".format(
                res.exit_code, code, res.output))
        return _perform_match(res.output, fnl)


def _perform_match(output, fnl):
    __tracebackhide__ = True
    if fnl:
        lm = LineMatcher(output.splitlines())
        lines = [x.strip() for x in fnl.strip().splitlines()]
        try:
            lm.fnmatch_lines(lines)
        except Exception:
            print(output)
            raise
    return output


@pytest.fixture
def cmd():
    """ invoke a command line subcommand with a unique plugin manager. """
    return ClickRunner()


@pytest.fixture
def mycmd(cmd, tmpdir, request):
    cmd.set_basedir(tmpdir.mkdir("account").strpath)
    return cmd
