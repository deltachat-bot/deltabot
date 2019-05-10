# -*- coding: utf-8 -*-
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
    acc = None
    plugins = None
    logger = None
    locale = None
