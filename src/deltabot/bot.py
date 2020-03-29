# -*- coding: utf-8 -*-

import deltachat as dc
from deltachat import account_hookimpl
from deltachat import Message, Contact
from deltachat.tracker import ConfigureTracker

from .commands import Commands
from .filters import Filters
from .plugins import Plugins


class DeltaBot:
    def __init__(self, account, logger):
        self.account = account

        self.logger = logger

        #: plugin subsystem for adding/removing plugins and calling plugin hooks
        self.plugins = Plugins(bot=self)

        #: commands subsystem for registering/executing '/*' commands in incoming messages
        self.commands = Commands(self)

        #: filter subsystem for registering/performing filters on incoming messages
        self.filters = Filters(self)

        # process dc events
        self._eventhandling = IncomingEventHandling(self)

        # set some useful bot defaults on the account
        self.account.update_config(dict(
            save_mime_headers=1,
            e2ee_enabled=1,
            sentbox_watch=0,
            mvbox_watch=0,
            bcc_self=0
        ))
        self.plugins.hook.deltabot_init.call_historic(kwargs=dict(bot=self))

    @property
    def self_contact(self):
        """ this bot's contact (with .addr and .display_name attributes). """
        return self.account.get_self_contact()

    def get_contact(self, ref):
        """ return Contact object (create one if needed) for the specified 'ref'.

        ref can be a Contact, email address string or contact id.
        """
        if isinstance(ref, str):
            return self.account.create_contact(ref)
        elif isinstance(ref, int):
            return self.account.get_contact_by_id(ref)
        elif isinstance(ref, Contact):
            return ref

    def get_chat(self, ref):
        """ Return a 1:1 chat (creating one if needed) from the specified ref object.

        ref can be a Message, Contact, email address string or chat-id integer.
        """
        if isinstance(ref, dc.message.Message):
            return self.account.create_chat_by_message(ref)
        elif isinstance(ref, dc.contact.Contact):
            return self.account.create_chat_by_contact(ref)
        elif isinstance(ref, str) and '@' in ref:
            return self.account.create_contact(ref).get_chat()
        elif type(ref) is int:
            try:
                return self.account.get_chat_by_id(ref)
            except ValueError:
                return None

    def create_group(self, name, members=[]):
        """ Create a new group chat. """
        group = self.account.create_group_chat(name)
        for member in map(self.get_contact, members):
            group.add_contact(member)
        return group

    def is_configured(self):
        """ Return True if this bot account is successfully configured. """
        return bool(self.account.is_configured())

    def perform_configure_address(self, email, password):
        """ perform initial email/password bot account configuration.  """
        assert not self.is_configured()
        assert not self.account._threads.is_started()
        with self.account.temp_plugin(ConfigureTracker()) as configtracker:
            self.account.update_config(dict(addr=email, mail_pw=password))
            self.account.start()
            try:
                configtracker.wait_finish()
            except configtracker.ConfigureFailed as ex:
                success = False
                self.logger.error('Failed to configure: {}'.format(ex))
            else:
                success = True
                self.logger.info('Successfully configured {}'.format(email))
            self.account.shutdown()
            return success

    def start(self):
        """ Start bot threads and processing messages. """
        addr = self.account.get_config("addr")
        self.logger.info("bot connected at: {}".format(addr))
        self.account.start()

    def wait_shutdown(self):
        """ Wait and block until bot account is shutdown. """
        self.account.wait_shutdown()


class IncomingEventHandling:
    def __init__(self, bot):
        self.bot = bot
        self.logger = bot.logger
        self.plugins = bot.plugins
        self.bot.account.add_account_plugin(self)

    @account_hookimpl
    def ac_incoming_message(self, message):
        try:
            # we always accept incoming messages to remove the need  for
            # bot authors to having to deal with deaddrop/contact requests.
            message.accept_sender_contact()
            self.logger.info("incoming message from {} id={} chat={} text={!r}".format(
                message.get_sender_contact().addr,
                message.id, message.chat.id, message.text[:50]))

            replies = Replies(message.account)
            self.plugins.hook.deltabot_incoming_message(
                message=message,
                bot=self.bot,
                replies=replies
            )
            for msg in replies.get_reply_messages():
                msg = message.chat.send_msg(msg)
                self.logger.info("reply id={} chat={} sent with text: {!r}".format(
                    msg.id, msg.chat, msg.text[:50]
                ))

        except Exception as ex:
            self.logger.exception(ex)

    @account_hookimpl
    def ac_message_delivered(self, message):
        self.logger.info("message id={} chat={} delivered to smtp".format(
            message.id, message.chat.id))


class Replies:
    def __init__(self, account):
        self.account = account
        self._replies = []

    def add(self, text=None, filename=None):
        """ Add a text or file-based reply. """
        self._replies.append((text, filename))

    def get_reply_messages(self):
        for text, file in self._replies:
            if file:
                view_type = "file"
            else:
                view_type = "text"
            msg = Message.new_empty(self.account, view_type)
            if text is not None:
                msg.set_text(text)
            if file is not None:
                msg.set_file(file)
            yield msg
