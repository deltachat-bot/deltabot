from abc import ABC, abstractmethod


__version__ = "0.8.0"


class Plugin(ABC):
    """Interface for the bot's  plugins."""

    name = None          # type: str
    description = None   # type: str
    version = None       # type: str
    author = None        # type: str
    author_email = None  # type: str

    def __init__(self, dc_account):
      self.acc = dc_account

    @staticmethod
    def get_args(cmd, text):
        """Return the args for the given command or None if the command does not match."""
        if text.startswith(cmd+' '):
            return text[len(cmd):].strip()
        elif text == cmd:
            return ''
        return None
            
    @abstractmethod
    def process(self, msg):
        """Return True if the message was processed with the plugin, False otherwise."""
