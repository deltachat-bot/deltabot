import pluggy


_name = "deltabot"
deltabot_hookspec = pluggy.HookspecMarker(_name)
deltabot_hookimpl = pluggy.HookimplMarker(_name)


class DeltaBotSpecs:
    """ per-Account-instance hook specifications.

    If you write a plugin you need to implement one of the following hooks.
    """
    @classmethod
    def _make_plugin_manager(cls):
        pm = pluggy.PluginManager(_name)
        pm.add_hookspecs(cls)
        return pm

    @deltabot_hookspec
    def deltabot_configure(self, bot):
        """ configure a bot instance. called Once at initialization"""
