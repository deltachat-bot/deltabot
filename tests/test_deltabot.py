
import os
import pytest


from deltabot.deltabot import DeltaBot
from deltabot.cmdline import make_logger


@pytest.fixture
def bot(acfactory):
    import logging
    account = acfactory.get_unconfigured_account()
    basedir = os.path.dirname(account.db_path)
    logger = make_logger(basedir, logging.DEBUG)
    return DeltaBot(account, logger)


def test_builtin_plugins(bot):
    assert "deltabot.builtin.echo" in bot.list_plugins()
    bot.remove_plugin(name="deltabot.builtin.echo")
    assert "deltabot.builtin.echo" not in bot.list_plugins()
