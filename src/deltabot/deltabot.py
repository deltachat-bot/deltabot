# -*- coding: utf-8 -*-

from collections import OrderedDict

import deltachat as dc
from deltachat import account_hookimpl
from deltachat.tracker import ConfigureTracker

from . import hookspec


CMD_PREFIX = '/'


class Filter():
    def __call__(self, msg):
        return False


class CommandDef:
    """ Definition of a '/COMMAND' with args. """
    def __init__(self, cmd, short, long, func):
        if cmd[0] != CMD_PREFIX:
            raise ValueError("cmd {!r} must start with {!}".format(cmd, CMD_PREFIX))
        self.cmd = cmd
        self.long = long
        self.short = short
        self.func = func

    def __eq__(self, c):
        return c.__dict__ == self.__dict__


class IncomingCommand:
    """ incoming command request. """
    def __init__(self, bot, cmd_def, payload, message):
        self.bot = bot
        self.cmd_def = cmd_def
        self.payload = payload
        self.message = message


class CommandNotFound(LookupError):
    """Command was not found. """


class DeltaBot:
    def __init__(self, account, logger):
        self.account = account
        self._pm = hookspec.DeltaBotSpecs._make_plugin_manager()
        self.logger = logger
        self._cmd_defs = OrderedDict()
        self.filters = []

        # set some useful bot defaults
        self.account.update_config(dict(
            save_mime_headers=1,
            e2ee_enabled=1,
            sentbox_watch=0,
            mvbox_watch=0,
            bcc_self=0
        ))
        self.account.add_account_plugin(self)
        self._register_builtin_plugins()
        self._pm.hook.deltabot_configure(bot=self)

    # =========================================================
    # deltabot plugin management  API
    # =========================================================

    def _register_builtin_plugins(self):
        self.logger.debug("registering builtin plugins")
        from deltabot.builtin import echo
        self.add_plugin_module("deltabot.builtin.echo", echo)

    def add_plugin_module(self, name, module):
        """ add a named deltabot plugin python module. """
        self.logger.debug("registering new plugin {!r}".format(name))
        self._pm.register(plugin=module, name=name)
        self._pm.check_pending()

    def remove_plugin(self, name):
        """ remove a named deltabot plugin. """
        self.logger.debug("removing plugin {!r}".format(name))
        self._pm.unregister(name=name)

    def list_plugins(self):
        """ return a dict name->deltabot plugin object mapping. """
        return dict(self._pm.list_name_plugin())

    # =========================================================
    # deltabot command API
    # =========================================================
    def register_command(self, name, func):
        short, long = parse_command_docstring(func)
        cmd_def = CommandDef(name, short=short, long=long, func=func)
        if name in self._cmd_defs:
            raise ValueError("command {!r} already registered".format(name))
        self._cmd_defs[name] = cmd_def
        self.logger.debug("registered new command {!r}".format(name))

    def _process_command_message(self, message):
        assert message.text.startswith(CMD_PREFIX)
        parts = message.text.split(maxsplit=1)
        cmd_name = parts.pop(0)
        cmd_def = self._cmd_defs.get(cmd_name)
        if cmd_def is None:
            raise CommandNotFound("unknown {!r} command in message {!r}".format(
                cmd_name, message))
        payload = parts[0] if parts else ""
        cmd = IncomingCommand(bot=self, cmd_def=cmd_def, payload=payload, message=message)
        return cmd.cmd_def.func(cmd)

    def is_configured(self):
        return bool(self.account.is_configured())

    def configure(self, email, password):
        with self.account.temp_plugin(ConfigureTracker()) as configtracker:
            self.account.update_config(dict(addr=email, mail_pw=password))
            self.account.start()
            try:
                configtracker.wait_finish()
            except configtracker.ConfigureFailed:
                self.logger.error('Bot configuration failed')
            else:
                self.logger.info('Bot configured successfully!')
            self.account.shutdown()

    def get_blobdir(self):
        return self.account.get_blobdir()

    def set_name(self, name):
        self.account.set_config('displayname', name)

    def send_file(self, chat, path, text, view_type='file'):
        msg = dc.message.Message.new_empty(self.account, view_type)
        msg.set_file(path)
        msg.set_text(text)
        chat.send_msg(msg)

    def add_filters(self, filters):
        self.filters.extend(filters)

    def remove_filters(self, filters):
        for f in filters:
            self.filters.remove(f)

    def add_filter(self, f):
        self.filters.append(f)

    def remove_filter(self, f):
        self.filters.remove(f)

    def on_message_delivered(self, msg):
        pass

    def start(self):
        self.account.start()

    def wait(self):
        self.account.wait_shutdown()

    @account_hookimpl
    def process_incoming_message(self, message):
        try:
            message.was_contact_request = message.chat.is_deaddrop()
            message.accept_sender_contact()
            if message.text and message.text.startswith(CMD_PREFIX):
                res = self._process_command_message(message)
                if res:
                    message.chat.send_text(res)
        except Exception as ex:
            self.logger.exception(ex)

    @account_hookimpl
    def process_message_delivered(self, message):
        try:
            self.on_message_delivered(message)
        except Exception as ex:
            self.logger.exception(ex)

    def get_contact(self, addr=None):
        if addr is None:
            return self.account.get_self_contact()
        else:
            return self.account.create_contact(addr.strip())

    def get_chat(self, ref):
        if type(ref) is dc.message.Message:
            return self.account.create_chat_by_message(ref)
        elif type(ref) is dc.contact.Contact:
            return self.account.create_chat_by_contact(ref)
        elif type(ref) is str and '@' in ref:
            c = self.account.create_contact(ref.strip())
            return self.account.create_chat_by_contact(c)
        elif type(ref) is int:
            try:
                return self.account.get_chat_by_id(ref)
            except ValueError:
                return None

    def get_chats(self):
        return self.account.get_chats()

    def get_address(self):
        return self.get_contact().addr

    def create_group(self, name, members=[]):
        group = self.account.create_group_chat(name)
        for member in members:
            if type(member) is str:
                member = self.account.create_contact(member.strip())
            group.add_contact(member)
        return group

    def is_group(self, chat):
        return chat.is_group()


def parse_command_docstring(func):
    description = func.__doc__
    if not description:
        raise ValueError("command {!r} needs to have a docstring".format(func))

    lines = description.strip().split("\n")
    return lines.pop(0), "\n".join(lines).strip()
