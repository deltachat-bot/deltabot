# -*- coding: utf-8 -*-
import json
import os
import re

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
    description = 'Provides the !friends command, use `!friends !help` for more info. Ex. !friends !join male,tech,free software,rock music.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    DB_PATH = os.path.abspath(os.path.expanduser('~/deltafriends.json'))  #TODO: use simplebot config dir and sqlite
    MAX_BIO_LEN = 60
    USER_ADDED = 'You are now in the DeltaFriends list'
    USER_REMOVED = 'You was removed from the DeltaFriends list'
    USER_NOT_FOUND = 'You are NOT in the DeltaFriends list'
    SEARCH_RESULTS = 'Search results for "{}":\n\n'
    NO_DESC = '(No description)'
    hcmd_list = '!friends !list command will return the list of users wanting to make new friends'
    hcmd_join = '!friends !join <bio> will add you to the list, "bio" is up to {} characters of words describing yourself. Ex. !friends !join male, Cuban, tech, free software, music'
    hcmd_leave = '!friends !leave command will remove you from the DeltaFriends list'
    hcmd_search = '!friends !search <text> search for friends which bio or email match the given text'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando !friends, para más información utilice !friends !help. Ej. !friends !join chico, música, tecnología, series, buscando amigos.'
            cls.USER_ADDED = 'Ahora estás en la lista de DeltaFriends'
            cls.USER_REMOVED = 'Fuiste eliminado de la lista de DeltaFriends'
            cls.USER_NOT_FOUND = 'No estás en la lista de DeltaFriends'
            cls.SEARCH_RESULTS = 'Resultados para "{}":\n\n'
            cls.NO_DESC = '(Sin descripción)'
            cls.hcmd_list = '!friends !list este comando te mostrará la lista de personas que buscan nuevos amigos'
            cls.hcmd_join = '!friends !join <bio> usa este comando para unirte a la lista, "<bio>" son palabras que te identifique o tus gustos (hasta {} caracteres). Ej. !friends !join programador, software libre, música, anime, CAV'
            cls.hcmd_leave = '!friends !leave usa este comando para quitarte de la lista de DeltaFriends'
            cls.hcmd_search = '!friends !search <texto> este comando permite buscar amigos basado en el texto que le pases. Ej. "!friends !search Habana" para buscar todas las personas que hayan dicho ser de La Habana'
        cls.friends = load_friends(cls.DB_PATH)

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!friends', msg.text)
        if arg is None:
            return False
        req = arg
        addr = msg.get_sender_contact().addr
        for cmd,action in [('!join', cls.join_cmd), ('!leave', cls.leave_cmd), ('!search', cls.search_cmd),
                           ('!list', cls.list_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                text = action(addr, arg)
                break
        else:
            text = cls.help_cmd()
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(text)
        return True

    @classmethod
    def list_cmd(cls, addr, text):
        get_desc = lambda d: d if d else cls.NO_DESC
        text = 'DeltaFriends(%s):\n\n' % len(cls.friends)
        text += '\n\n'.join(['%s: %s' % (addr,get_desc(desc))
                             for addr,desc in sorted(cls.friends.items())])
        return text        

    @classmethod
    def join_cmd(cls, addr, text):
        text = ' '.join([word for word in text.split()])
        if len(text) > cls.MAX_BIO_LEN:
            text = text[:cls.MAX_BIO_LEN] + '...'
        cls.friends[addr] = text
        save_friends(cls.friends, cls.DB_PATH)
        return cls.USER_ADDED

    @classmethod
    def leave_cmd(cls, addr, text):
        try:
            cls.friends.pop(addr)
            save_friends(cls.friends, cls.DB_PATH)
            return cls.USER_REMOVED
        except KeyError:
            return cls.USER_NOT_FOUND

    @classmethod
    def search_cmd(cls, _, text):
        friends = ''
        get_desc = lambda d: d if d else cls.NO_DESC
        t = re.compile(text, re.IGNORECASE)
        for addr,desc in sorted(cls.friends.items()):
            desc = get_desc(desc)
            if t.findall(desc) or t.findall(addr):
                friends += '{}: {}\n\n'.format(addr, desc)
        return cls.SEARCH_RESULTS.format(text)+friends

    @classmethod
    def help_cmd(cls):
        return '\n\n'.join(['DeltaFriends:\n', cls.hcmd_list, cls.hcmd_join.format(cls.MAX_BIO_LEN),
                            cls.hcmd_search, cls.hcmd_leave])
