
import pluggy

spec_name = "deltabot"
deltabot_hookspec = pluggy.HookspecMarker(spec_name)
deltabot_hookimpl = pluggy.HookimplMarker(spec_name)


class DeltaBotSpecs:
    """ per DeltaBot instance hook specifications.

    If you write a plugin you probably want to implement one or more hooks.
    """
    @deltabot_hookspec(historic=True)
    def deltabot_init(self, bot):
        """ initialize a bot instance. called before the bot starts serving requests.

        Note that plugins that register after DeltaBot initizliation
        will still be called to have a chance to register their
        commands and filters.
        """

    @deltabot_hookspec
    def deltabot_incoming_message(self, message, bot):
        """ process an incoming message, optionally returning a Reply object.

        If a Reply is returned, it will be sent back to
        the chat where the original message came in.
        """
