# -*- coding: utf-8 -*-
import os
import re
import sqlite3

from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape


class DeltaFriends(Plugin):

    name = 'DeltaFriends'
    description = 'Provides the !friends command.'
    long_description = 'Ex. !friends !join male,tech,free software,rock music.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!friends'

    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'
    MAX_BIO_LEN = 250
    USER_ADDED = 'You are now in the DeltaFriends list'
    USER_REMOVED = 'You was removed from the DeltaFriends list'
    USER_NOT_FOUND = 'You are NOT in the DeltaFriends list'
    SEARCH_RESULTS = 'Search results for "{}":\n\n'
    NO_DESC = '(No description)'
    hcmd_list = '!friends !list command will return the list of users wanting to make new friends'
    hcmd_join = '!friends !join <bio> will add you to the list or update your bio, "bio" is up to {} characters of words describing yourself. Ex. !friends !join male, Cuban, tech, free software, music'
    hcmd_leave = '!friends !leave command will remove you from the DeltaFriends list'
    hcmd_search = '!friends !search <text> search for friends which bio or email match the given text'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.template = env.get_template('index.html')
        cls.conn = sqlite3.connect(os.path.join(cls.ctx.basedir, 'deltafriends.db'))
        with cls.conn:
            cls.conn.execute('''CREATE TABLE IF NOT EXISTS deltafriends (addr TEXT NOT NULL, bio TEXT, PRIMARY KEY(addr))''')
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando !friends, para más información utilice !friends !help. Ej. !friends !join chico, música, tecnología, series, buscando amigos.'
        #     cls.USER_ADDED = 'Ahora estás en la lista de DeltaFriends'
        #     cls.USER_REMOVED = 'Fuiste eliminado de la lista de DeltaFriends'
        #     cls.USER_NOT_FOUND = 'No estás en la lista de DeltaFriends'
        #     cls.SEARCH_RESULTS = 'Resultados para "{}":\n\n'
        #     cls.NO_DESC = '(Sin descripción)'
        #     cls.hcmd_list = '!friends !list este comando te mostrará la lista de personas que buscan nuevos amigos'
        #     cls.hcmd_join = '!friends !join <bio> usa este comando para unirte a la lista o actualizar tu biografía, "<bio>" son palabras que te identifique o tus gustos (hasta {} caracteres). Ej. !friends !join programador, software libre, música, anime, CAV'
        #     cls.hcmd_leave = '!friends !leave usa este comando para quitarte de la lista de DeltaFriends'
        #     cls.hcmd_search = '!friends !search <texto> este comando permite buscar amigos basado en el texto que le pases. Ej. "!friends !search Habana" para buscar todas las personas que hayan dicho ser de La Habana'

    @classmethod
    def deactivate(cls, ctx):
        cls.conn.close()

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!friends', msg.text)
        if arg is None:
            return False
        req = arg
        addr = msg.get_sender_contact().addr
        chat = cls.ctx.acc.create_chat_by_message(msg)
        for cmd,action in [('!join', cls.join_cmd), ('!leave', cls.leave_cmd), ('!search', cls.search_cmd),
                           ('!list', cls.list_cmd), ('!help', cls.help_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                chat.send_text(action(addr, arg))
                break
        else:
            if not req:
                html = cls.template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr)
                with open(cls.TEMP_FILE, 'w') as fd:
                    fd.write(html)
                chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True

    @classmethod
    def list_cmd(cls, addr, text):
        friends = cls.conn.execute('SELECT * FROM deltafriends ORDER BY addr').fetchall()
        get_desc = lambda d: d if d else cls.NO_DESC
        text = 'DeltaFriends({}):\n\n'.format(len(friends))
        text += '\n\n'.join(['🔘 {}: {}'.format(addr, get_desc(desc))
                             for addr,desc in friends])
        return text

    @classmethod
    def join_cmd(cls, addr, text):
        bio = ' '.join([word for word in text.split()])
        if len(bio) > cls.MAX_BIO_LEN:
            bio = bio[:cls.MAX_BIO_LEN] + '...'
        with cls.conn:
            cls.conn.execute('INSERT OR REPLACE INTO deltafriends VALUES (?, ?)', (addr, bio))
        return cls.USER_ADDED

    @classmethod
    def leave_cmd(cls, addr, _):
        with cls.conn:
            rowcount = cls.conn.execute('DELETE FROM deltafriends WHERE addr=?', addr).rowcount
        if rowcount == 1:
            return cls.USER_REMOVED
        else:
            return cls.USER_NOT_FOUND

    @classmethod
    def search_cmd(cls, _, text):
        results = ''
        get_desc = lambda d: d if d else cls.NO_DESC
        t = re.compile(text, re.IGNORECASE)
        for addr,desc in cls.conn.execute('SELECT * FROM deltafriends ORDER BY addr'):
            desc = get_desc(desc)
            if t.findall(desc) or t.findall(addr):
                results += '🔘 {}: {}\n\n'.format(addr, desc)
        return cls.SEARCH_RESULTS.format(text)+results

    @classmethod
    def help_cmd(cls, *args):
        return '\n\n'.join(['DeltaFriends:\n', cls.hcmd_list, cls.hcmd_join.format(cls.MAX_BIO_LEN),
                            cls.hcmd_search, cls.hcmd_leave])
