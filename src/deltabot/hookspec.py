
import pluggy

spec_name = "deltabot"
deltabot_hookspec = pluggy.HookspecMarker(spec_name)
deltabot_hookimpl = pluggy.HookimplMarker(spec_name)


class DeltaBotSpecs:
    """ per DeltaBot instance hook specifications. """

    @deltabot_hookspec(historic=True)
    def deltabot_init(self, bot):
        """ init a bot -- called before the bot starts serving requests.

        Note that plugins that register after DeltaBot initizialition
        will still be called in order to allow them registering their
        commands and filters.
        """

    @deltabot_hookspec(firstresult=True)
    def deltabot_incoming_message(self, message, bot, replies):
        """ process an incoming fresh message.

        :param replies: call replies.add() to schedule a reply.
        """
