
import pluggy

spec_name = "deltabot"
deltabot_hookspec = pluggy.HookspecMarker(spec_name)
deltabot_hookimpl = pluggy.HookimplMarker(spec_name)


class DeltaBotSpecs:
    """ per DeltaBot instance hook specifications. """

    @deltabot_hookspec
    def deltabot_init_parser(self, parser):
        """ initialize the deltabot main parser with new options and subcommands.

        :param parser: a :class:`deltabot.parser.MyArgumentParser` instance where you can
                        call `add_subcommand(name, func)` to get a sub parser where you
                        can then add arguments.
        """

    @deltabot_hookspec
    def deltabot_add_generic_options(self, parser, subcommand_name):
        """ add generic option to a (sub) parser.

        :param parser: a :class:`deltabot.parser.MyArgumentParser` instance where you can
                        call `add_subcommand(name, func)` to get a sub parser where you
                        can then add arguments.
        :param subcommand_name: sub command name or None if this is the top level parser.
        """

    @deltabot_hookspec(historic=True)
    def deltabot_init(self, bot):
        """ init a bot -- called before the bot starts serving requests.

        Note that plugins that register after DeltaBot initizialition
        will still be called in order to allow them registering their
        commands and filters.
        """

    @deltabot_hookspec
    def deltabot_shutdown(self, bot):
        """ shutdown all resources of the bot. """

    @deltabot_hookspec(firstresult=True)
    def deltabot_incoming_message(self, message, bot, replies):
        """ process an incoming fresh message.

        :param replies: call replies.add() to schedule a reply.
        """

    @deltabot_hookspec(firstresult=True)
    def deltabot_store_setting(self, key, value):
        """ store a named bot setting persistently. """

    @deltabot_hookspec(firstresult=True)
    def deltabot_get_setting(self, key):
        """ get a named persistent bot setting."""
