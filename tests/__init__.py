from unittest.mock import Mock
import unittest
import os
import sys


def setUpModule():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # allow to import simplebot
    sys.path.insert(0, root)

    # allow to import plugins
    plugins_dir = os.path.join(root, 'plugins')
    for plugin in os.listdir(plugins_dir):
        sys.path.insert(0, os.path.join(plugins_dir, plugin))


class TestSimplebot(unittest.TestCase):
    pass


class TestEcho(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from simplebot_echo import Echo
        import simplebot

        cls.p = Echo
        cls.bot = Mock(simplebot.SimpleBot)
        cls.bot.locale = 'en'

        # set cls.p.bot to cls.bot:
        cls.p.activate(cls.bot)

    def test_echo_cmd(self):
        ctx = Mock()

        ctx.msg = 't1'
        ctx.text = None
        self.p.echo_cmd(ctx)
        self.bot.get_chat(ctx.msg).send_text.assert_called_with('🤖')

        ctx.text = 't2'
        ctx.msg = ctx.text
        self.p.echo_cmd(ctx)
        self.bot.get_chat(ctx.msg).send_text.assert_called_with('t2')
