
import pluggy

from .hookspec import spec_name, DeltaBotSpecs


class Plugins:
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self._pm = pluggy.PluginManager(spec_name)
        self._pm.add_hookspecs(DeltaBotSpecs)
        self.hook = self._pm.hook
        self._register_builtin_plugins()

    def _register_builtin_plugins(self):
        self.logger.debug("registering builtin plugins")
        from deltabot.builtin import echo, db
        self.add_module(echo.__name__, echo)
        self.add_module(db.__name__, db)

    def add_module(self, name, module):
        """ add a named deltabot plugin python module. """
        self.logger.debug("registering new plugin {!r}".format(name))
        self._pm.register(plugin=module, name=name)
        self._pm.check_pending()

    def remove(self, name):
        """ remove a named deltabot plugin. """
        self.logger.debug("removing plugin {!r}".format(name))
        self._pm.unregister(name=name)

    def dict(self):
        """ return a dict name->deltabot plugin object mapping. """
        return dict(self._pm.list_name_plugin())

    def items(self):
        """ return (name, plugin obj) list. """
        return self._pm.list_name_plugin()
