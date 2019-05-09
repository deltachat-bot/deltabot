from abc import ABC, abstractmethod


__version__ = "0.8.0"


class Plugin(ABC):
    """Interface for the bot's  plugins."""

    name = None          # type: str
    description = None   # type: str
    version = None       # type: str
    author = None        # type: str
    author_email = None  # type: str

    @staticmethod
    def get_args(cmd, text):
        """Return the args for the given command or None if the command does not match."""
        if text.startswith(cmd+' '):
            return text[len(cmd):].strip()
        elif text == cmd:
            return ''
        return None
            
    @staticmethod
    @abstractmethod
    def process(msg):
        """Return True if the message was processed with the plugin, False otherwise."""
        
    @staticmethod
    def activate(ctx):
        """Activate the plugin, this method is called at the start of the bot."""
        pass

    @staticmethod
    def deactivate(ctx):
        """Deactivate the plugin, this method is called to disable/stop the plugin."""
        pass

