
import pluggy

spec_name = "deltabot"
deltabot_hookspec = pluggy.HookspecMarker(spec_name)
deltabot_hookimpl = pluggy.HookimplMarker(spec_name)


class DeltaBotSpecs:
    """ per DeltaBot instance hook specifications.

    If you write a plugin you probably want to implement one or more hooks.
    """
    @deltabot_hookspec(historic=True)
    def deltabot_configure(self, bot):
        """ configure a bot instance. called Once at initialization"""

    @deltabot_hookspec
    def deltabot_process_incoming(self, message, bot):
        """ process an incoming message and return a reply Message or None.

        If a reply message is returned, it will be sent back to
        the chat where the original message came in.
        """
