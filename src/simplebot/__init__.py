# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import re


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
        if re.match(cmd+r'\b', text):
            return text[len(cmd):].strip()
        return None
            
    @classmethod
    @abstractmethod
    def process(cls, msg):
        """Return True if the message was processed with the plugin, False otherwise."""

    @classmethod
    def activate(cls, ctx):
        """Activate the plugin, this method is called at the start of the bot."""
        cls.ctx = ctx

    @classmethod
    def deactivate(cls, ctx):
        """Deactivate the plugin, this method is called before the plugin is disabled/removed, do clean up here."""
        pass


class Context:
    """Context for plugins"""
    # deltachat.account.Account instance
    acc = None
    # the list of installed plugins
    plugins = None
    # logging.Logger compatible instance
    logger = None
    # locale to start the bot: es, en, etc.
    locale = None
    # base directory for the bot configuration and db files
    basedir = None
