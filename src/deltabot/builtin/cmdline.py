
import argparse
import os

from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init_parser(parser):
    parser.add_subcommand(Init)
    parser.add_subcommand(Info)
    parser.add_subcommand(ListPlugins)
    parser.add_subcommand(Serve)


@deltabot_hookimpl
def deltabot_add_generic_options(group, subcommand_name):
    group.add_argument(
        "--version", action="store_true",
        help="show program's version number and exit")
    group.add_argument(
        "-v", "--verbose", action="count", default=0, help="increase verbosity")
    group.add_argument(
        "--stdout-loglevel", choices=["info", "debug", "err", "warn"],
        default="info", help="stdout logging level.")
    # workaround for http://bugs.python.org/issue23058
    if subcommand_name is None:
        basedir_default = os.path.expanduser(
            os.environ.get("DELTABOT_BASEDIR", "~/.config/deltabot"))
    else:
        # subcommands will have their default being suppressed, so only the
        # main one is used
        basedir_default = argparse.SUPPRESS
    group.add_argument(
        "--basedir", action="store", metavar="DIR",
        default=basedir_default,
        help="directory for storing all deltabot state")


class Init:
    """initialize account with emailadr and password.

    This will set and verify smtp/imap connectivity using the provided credentials.
    """
    def add_arguments(self, parser):
        parser.add_argument("emailaddr", metavar="ADDR", type=str)
        parser.add_argument("password", type=str)

    def run(self, bot, args, out):
        if "@" not in args.emailaddr:
            out.fail("invalid email address: {!r}".format(args.emailaddr))
        success = bot.perform_configure_address(args.emailaddr, args.password)
        if not success:
            out.fail("failed to configure with: {}".format(args.emailaddr))


class Info:
    """show information about configured account. """

    def run(self, bot, args, out):
        if not bot.is_configured():
            out.fail("account not configured, use 'deltabot init'")

        for key, val in bot.account.get_info().items():
            out.line("{:30s}: {}".format(key, val))


class ListPlugins:
    """list deltabot plugins. """
    name = "list-plugins"

    def run(self, bot, args, out):
        for name, plugin in bot.plugins.items():
            out.line("{:25s}: {}".format(name, plugin))


class Serve:
    """serve and react to incoming messages"""

    def run(self, bot, args, out):
        if not bot.is_configured():
            out.fail("account not configured: {}".format(bot.account.db_path))

        bot.start()
        bot.account.wait_shutdown()
