
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    parser.add_subcommand(db_set)
    parser.add_subcommand(db_get)
    parser.add_subcommand(db_list)


@deltabot_hookimpl
def deltabot_init(bot):
    bot.commands.register(name="/get", func=command_get)
    bot.commands.register(name="/set", func=command_set)


def slash_scoped_key(key):
    i = key.find("/")
    if i == -1:
        raise ValueError("key {!r} does not contain a '/' scope delimiter")
    return (key[:i], key[i + 1:])


class db_get:
    """Get a low level setting."""

    def add_arguments(self, parser):
        parser.add_argument("key", type=slash_scoped_key, help="low level database key")

    def run(self, bot, args, out):
        scope, key = args.key
        res = bot.get(key, scope=scope)
        if res is None:
            out.fail("key {} does not exist".format("/".join(args.key)))
        else:
            out.line(res)


class db_set:
    """Set a low level setting."""

    def add_arguments(self, parser):
        parser.add_argument("key", type=slash_scoped_key, help="low level database key")
        parser.add_argument("value", type=str, help="low level key value")

    def run(self, bot, args, out):
        scope, key = args.key
        bot.set(key, args.value, scope=scope)


class db_list:
    """List all key,values. """

    def add_arguments(self, parser):
        parser.add_argument(
            "--scope", type=str,
            help="slash-terminated scope of db key", default=None)

    def run(self, bot, args, out):
        res = bot.list_settings(args.scope)
        for key, res in res:
            out.line("{}: {}".format(key, res))


def command_get(command):
    """get value for a key. If no key is specified, return all settings."""
    addr = command.message.get_sender_contact().addr
    lines = []
    if len(command.args) == 0:
        lines.extend(dump_settings(command.bot, scope=addr))
    else:
        x = command.bot.get(command.args[0], scope=addr)
        lines.append("{}={}".format(command.args[0], x))
    return "\n".join(lines)


def command_set(command):
    """get value for a key. If no key is specified, return all settings."""
    addr = command.message.get_sender_contact().addr
    if len(command.args) == 2:
        name, value = command.args
        old = command.bot.set(name, value, scope=addr)
        return "old: {}={}".format(name, repr(old))
    elif len(command.args) == 0:
        return "\n".join(dump_settings(command.bot, scope=addr))


def dump_settings(bot, scope):
    lines = []
    for name, value in bot.list_settings(scope=scope):
        lines.append("{}={}".format(name, value))
    if not lines:
        lines.append("no settings")
    return lines


class TestCommandSettings:
    def test_mock_get_set_empty_settings(self, mocker):
        reply_msg = mocker.run_command("/get")
        assert reply_msg.text.startswith("no settings")
        reply_msg = mocker.run_command("/set")
        assert reply_msg.text.startswith("no settings")

    def test_mock_set_works(self, mocker):
        reply_msg = mocker.run_command("/set hello world")
        assert "old" in reply_msg.text
        msg_reply = mocker.run_command("/get")
        assert "hello=world" == msg_reply.text

    def test_get_set_functional(self, bot_tester):
        msg_reply = bot_tester.send_command("/set hello world")
        assert "old" in msg_reply.text
        msg_reply = bot_tester.send_command("/set hello2 world2")
        msg_reply = bot_tester.send_command("/get hello")
        assert msg_reply.text == "hello=world"
        msg_reply = bot_tester.send_command("/get")
        assert "hello=world" in msg_reply.text
        assert "hello2=world2" in msg_reply.text
