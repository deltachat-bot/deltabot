# -*- coding: utf-8 -*-
from abc import ABC, abstractmethod
import configparser
import logging
import os
import re
import zipfile
import zlib

from .deltabot import DeltaBot
import pkg_resources


__version__ = '0.9.0'


class Plugin(ABC):
    """Interface for the bot's  plugins."""

    name = ''
    description = ''
    long_description = ''
    version = ''
    commands = []

    @classmethod
    def on_message_detected(cls, msg, text):
        """Return the new text to be passed to messages listeners or None if the message should be rejected."""
        return text

    @classmethod
    def on_message(cls, msg):
        """Returns True if the message was processed, False otherwise."""
        return False

    @classmethod
    def on_message_processed(cls, msg, processed):
        """processed is True if the message was processed, False otherwise."""
        pass

    @classmethod
    def on_command_detected(cls, msg, text):
        """Return the new text to be passed to commands listeners or None if the message should be rejected."""
        return text

    @classmethod
    def on_command_processed(cls, msg, processed):
        """processed is True if the message was processed, False otherwise."""
        pass

    @classmethod
    def activate(cls, bot):
        """Activate the plugin, this method is called when the bot starts."""
        cls.bot = bot

    @classmethod
    def deactivate(cls, ctx):
        """Deactivate the plugin, this method is called before the plugin is disabled/removed, do clean up here."""
        pass


class SimpleBot(DeltaBot):
    # deltachat.account.Account instance
    account = None
    # the list of installed plugins
    plugins = None
    # logging.Logger compatible instance
    logger = None
   # locale to start the bot: es, en, etc.
    locale = 'en'
    # base directory for the bot configuration and db files
    basedir = None

    def __init__(self, basedir):
        super().__init__(basedir)
        self._load_config(os.path.join(self.basedir, 'simplebot.cfg'))
        self._on_message_detected_listeners = set()
        self._on_message_listeners = set()
        self._on_message_processed_listeners = set()
        self._on_command_detected_listeners = set()
        self._on_command_processed_listeners = set()
        self.load_plugins()
        self.activate_plugins()

    def send_html(self, chat, html, basename, user_agent):
        if user_agent == 'zhv':
            file_path = basename+'.htmlzip'
            zlib.Z_DEFAULT_COMPRESSION = 9
            with zipfile.ZipFile(file_path, 'w', compression=zipfile.ZIP_DEFLATED) as fd:
                fd.writestr('index.html', html)
            chat.send_file(file_path)
        else:
            file_path = basename+'.html'
            with open(file_path, 'w') as fd:
                fd.write(html)
            chat.send_file(file_path, mime_type='text/html')

    def _load_config(self, cfg_path):
        cfg = configparser.ConfigParser(allow_no_value=True)
        if os.path.exists(cfg_path):
            cfg.read(cfg_path)
            botcfg = cfg['simplebot']
        else:
            cfg.add_section('simplebot')
            botcfg = cfg['simplebot']
        cfg['DEFAULT']['displayname'] = 'SimpleBot🤖'
        cfg['DEFAULT']['mdns_enabled'] = '0'
        cfg['DEFAULT']['mvbox_move'] = '1'
        with open(cfg_path, 'w') as fd:
            cfg.write(fd)
        self.set_name(botcfg['displayname'])
        self.account.set_config('mdns_enabled', botcfg['mdns_enabled'])
        self.account.set_config('mvbox_move', botcfg['mvbox_move'])

    def add_on_message_detected_listener(self, listener):
        self._on_message_detected_listeners.add(listener)

    def add_on_message_listener(self, listener):
        self._on_message_listeners.add(listener)

    def add_on_message_processed_listener(self, listener):
        self._on_message_processed_listeners.add(listener)

    def remove_on_message_detected_listener(self, listener):
        self._on_message_detected_listeners.remove(listener)

    def remove_on_message_listener(self, listener):
        self._on_message_listeners.remove(listener)

    def remove_on_message_processed_listener(self, listener):
        self._on_message_processed_listeners.remove(listener)

    def add_on_command_detected_listener(self, listener):
        self._on_command_detected_listeners.add(listener)

    def add_on_command_processed_listener(self, listener):
        self._on_command_processed_listeners.add(listener)

    def remove_on_command_detected_listener(self, listener):
        self._on_command_detected_listeners.remove(listener)

    def remove_on_command_processed_listener(self, listener):
        self._on_command_processed_listeners.remove(listener)

    def on_message_delivered(self, msg):
        self.account.delete_messages((msg,))

    def on_message(self, msg):
        self.logger.debug('Received message from {}'.format(
            msg.get_sender_contact().addr,))

        if msg.get_mime_headers()['chat-version'] is None:
            self.logger.debug('Classic email rejected')
            self.account.delete_messages((msg,))
            return

        for l in self._on_message_detected_listeners:
            try:
                if not l.on_message_detected(msg):
                    self.logger.debug('Message rejected by '+plugin.name)
                    self.account.delete_messages((msg,))
                    return
            except Exception as ex:
                self.logger.exception(ex)

        for l in self._on_message_listeners:
            try:
                if l.on_message(msg):
                    self.logger.debug('Message processed by '+plugin.name)
                    processed = True
                    break
            except Exception as ex:
                self.logger.exception(ex)
        else:
            processed = False
            self.logger.debug('Message was not processed.')
        for l in self._on_message_processed_listeners:
            try:
                l.on_message_processed(msg, processed)
            except Exception as ex:
                self.logger.exception(ex)

        self.account.mark_seen_messages([msg])

    def on_command(self, msg):
        self.logger.debug('Received command from {}'.format(
            msg.get_sender_contact().addr,))

        if msg.get_mime_headers()['chat-version'] is None:
            self.logger.debug('Classic email rejected')
            self.account.delete_messages((msg,))
            return

        real_cmd = self.get_args('/zhv', msg)
        if real_cmd is None:
            msg.user_agent = 'unknow'
            text = msg.text
        else:
            msg.user_agent = 'zhv'
            text = real_cmd
        for l in self._on_command_detected_listeners:
            try:
                text = l.on_command_detected(msg)
                if text is None:
                    self.logger.debug('Command rejected by '+plugin.name)
                    self.account.delete_messages((msg,))
                    return
            except Exception as ex:
                self.logger.exception(ex)

        for cmd in self.commands:
            args = self.get_args(cmd, text)
            if args is not None:
                try:
                    self.commands[cmd][-1](msg, args)
                    processed = True
                    break
                except Exception as ex:
                    self.logger.exception(ex)
        else:
            processed = False

        if not processed:
            self.logger.debug('Message was not processed.')

        for l in self._on_command_processed_listeners:
            try:
                l.on_command_processed(msg, processed)
            except Exception as ex:
                self.logger.exception(ex)

        self.account.mark_seen_messages([msg])

    def load_plugins(self):
        self.plugins = []
        for ep in pkg_resources.iter_entry_points('simplebot.plugins'):
            try:
                self.plugins.append(ep.load())
            except Exception as ex:
                self.logger.exception(ex)

    def activate_plugins(self):
        for plugin in self.plugins:
            plugin.activate(self)

    def deactivate_plugins(self):
        for plugin in self.plugins:
            try:
                plugin.deactivate(self)
            except Exception as ex:
                self.logger.exception(ex)
