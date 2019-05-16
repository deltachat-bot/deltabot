# -*- coding: utf-8 -*-
import json
import os

from simplebot import Plugin


def load_friends(db_path):
    try:
        with open(db_path) as fd:
            return json.load(fd)
    except FileNotFoundError:
        return dict()


def save_friends(friends, db_path):
    with open(db_path, 'w') as fd:
        json.dump(friends, fd)

class DeltaFriends(Plugin):

    name = 'DeltaFriends'
    description = 'Provides the !friends command, use `!friends !help` for more info. Ex. !friends !join Interestedin tech and free software.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    DB_PATH = os.path.abspath(os.path.expanduser('~/deltafriends.json'))  #TODO: use simplebot config dir
    USER_ADDED = 'You are now in the DeltaFriends list'
    USER_REMOVED = 'You was removed from the DeltaFriends list'
    USER_NOT_FOUND = 'You are NOT in the DeltaFriends list'
    NO_DESC = '(No description)'
    hcmd_list = '!friends command will return the list of users wanting to make new friends'
    hcmd_join = '!friends !join <bio> will add you to the list, "bio" is up to 50 characters of words describing yourself. Ex. !friends !join male, Cuban, tech, free software, music'
    hcmd_leave = '!friends !leave command will remove you from the DeltaFriends list'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando !friends, para más información utilice !friends !help. Ej. !friends !join intereses: tecnología, software libre.'
            cls.USER_ADDED = 'Ahora estás en la lista de DeltaFriends'
            cls.USER_REMOVED = 'Fuiste eliminado de la lista de DeltaFriends'
            cls.USER_NOT_FOUND = 'No estás en la lista de DeltaFriends'
            cls.NO_DESC = '(Sin descripción)'
            cls.hcmd_list = '!friends este comando te mostrará la lista de personas que buscan nuevos amigos'
            cls.hcmd_join = '!friends !join <bio> usa este comando para unirte a la lista, "<bio>" son palabras que te identifique o tus gustos (hasta 50 caracteres). Ej. !friends !join programador, software libre, música, anime, CAV'
            cls.hcmd_leave = '!friends !leave usa este comando para quitarte de la lista de DeltaFriends'
        cls.friends = load_friends(cls.DB_PATH)

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!friends', msg.text)
        if arg is None:
            return False
        if not arg:
            text = cls.dump_friends()
            chat = cls.ctx.acc.create_chat_by_message(msg)
        else:
            req = arg
            addr = msg.get_sender_contact().addr
            for cmd,action in [('!join', cls.join), ('!leave', cls.leave)]:
                arg = cls.get_args(cmd, req)
                if arg is not None:
                    text = action(addr, arg)
                    chat = cls.ctx.acc.create_chat_by_contact(msg.get_sender_contact)
                    break
            else:
                text = cls.get_help()
                chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True

    @classmethod
    def dump_friends(cls):
        get_desc = lambda d: d if d else cls.NO_DESC
        text = 'DeltaFriends(%s):\n\n' % len(cls.friends)
        text += '\n\n'.join(['%s: %s' % (addr,get_desc(desc))
                             for addr,desc in sorted(cls.friends.items(), key=lambda u: u[0])])
        return text        

    @classmethod
    def join(cls, addr, text):
        text = ' '.join([word for word in text.split()])
        if len(text) > 50:
            text = text[:50] + '...'
        cls.friends[addr] = text
        save_friends(cls.friends, cls.DB_PATH)
        return cls.USER_ADDED

    @classmethod
    def leave(cls, addr, text):
        try:
            cls.friends.pop(addr)
            save_friends(cls.friends, cls.DB_PATH)
            return cls.USER_REMOVED
        except KeyError:
            return cls.USER_NOT_FOUND

    @classmethod
    def get_help(cls):
        return '\n\n'.join(['DeltaFriends:\n', cls.hcmd_list, cls.hcmd_join, cls.hcmd_leave])
