
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    parser.add_subcommand(db_set)
    parser.add_subcommand(db_get)
    parser.add_subcommand(db_list)


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
