# -*- coding: utf-8 -*-
import os
import re

import deltachat as dc


_CMD_PREFIX = '/'


class DeltaBot:
    def __init__(self, basedir):
        self.commands = dict()
        self.basedir = os.path.abspath(os.path.expanduser(basedir))
        self.account = _get_account(self.basedir)
        self.account.set_config('save_mime_headers', '1')
        self.account.set_config('e2ee_enabled', '1')
        self.account.set_config('sentbox_watch', '0')
        self.account.set_config('mvbox_watch', '0')

    def is_configured(self):
        return bool(self.account.is_configured())

    def configure(self, email, password):
        self.account.configure(addr=email, mail_pw=password)
        self.account.start_threads()
        _wait_configuration_progress(self.account, 1000)
        self.account.stop_threads()

    def set_name(self, name):
        self.account.set_config('displayname', name)

    def add_commands(self, commands):
        for cmd in commands:
            self.add_command(*cmd)

    def remove_commands(self, commands):
        for cmd in commands:
            self.remove_command(cmd[0])

    def add_command(self, cmd, args, description, action):
        if not cmd.startswith(_CMD_PREFIX):
            raise ValueError('Commands must start with {}'.format(_CMD_PREFIX))
        self.commands[cmd] = (args, description, action)

    def remove_command(self, cmd):
        del self.commands[cmd]

    @staticmethod
    def get_args(cmd, msg):
        """Return the args for the given command or None if the command does not match."""
        if type(msg) is dc.message.Message:
            msg = msg.text
        if re.match(r'{}\b'.format(cmd), msg, re.IGNORECASE):
            return msg[len(cmd):].strip()
        return None

    def on_message(self, msg):
        pass

    def on_command(self, msg):
        for cmd in self.commands:
            args = self.get_args(cmd, msg)
            if args is not None:
                try:
                    self.commands[cmd][-1](msg, args)
                    return True
                except Exception as ex:
                    self.logger.exception(ex)
        else:
            return False

    def start(self):
        self.account.start_threads()
        try:
            while True:
                ev = self.account._evlogger.get()
                if ev[0] in ('DC_EVENT_MSGS_CHANGED', 'DC_EVENT_INCOMING_MSG') and ev[2] != 0:
                    msg = self.account.get_message_by_id(int(ev[2]))
                    if msg.get_sender_contact() == self.account.get_self_contact():
                        # self.account.delete_messages((msg,))
                        continue
                    msg.contact_request = (ev[0] == 'DC_EVENT_MSGS_CHANGED')
                    if msg.text and msg.text.startswith(_CMD_PREFIX):
                        self.on_command(msg)
                    else:
                        self.on_message(msg)
        finally:
            self.account.stop_threads()

    def get_contact(self, addr):
        return self.account.create_contact(addr.strip())

    def get_chat(self, ref):
        if type(ref) is dc.message.Message:
            return self.account.create_chat_by_message(ref)
        elif type(ref) is dc.chatting.Contact:
            return self.account.create_chat_by_contact(ref)
        elif type(ref) is str and '@' in ref:
            c = self.account.create_contact(ref.strip())
            return self.account.create_chat_by_contact(c)
        elif type(ref) is int:
            return dc.chatting.Chat(self.account._dc_context, ref)

    def get_chats(self):
        return self.account.get_chats()

    def get_address(self):
        return self.account.get_self_contact().addr

    def create_group(self, name, members=[]):
        group = self.account.create_group_chat(name)
        for member in members:
            if type(member) is str:
                member = self.account.create_contact(member.strip())
            group.add_contact(member)
        return group


def _wait_configuration_progress(account, target):
    while 1:
        evt_name, data1, data2 = \
            account._evlogger.get_matching("DC_EVENT_CONFIGURE_PROGRESS")
        if data1 >= target:
            print("** CONFIG PROGRESS {}".format(target), account)
            return data1


def _get_account(basedir):
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    db_path = os.path.join(basedir, "account.db")
    acc = dc.Account(db_path)
    acc.db_path = db_path
    return acc
