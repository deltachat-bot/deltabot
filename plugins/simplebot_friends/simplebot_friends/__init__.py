# -*- coding: utf-8 -*-
import os
import re
import sqlite3

from simplebot import Plugin
from jinja2 import Environment, PackageLoader, select_autoescape


class DeltaFriends(Plugin):

    name = 'DeltaFriends'
    description = 'Provides the !friends command.'
    long_description = '<ul><li>!friends !list command will return the list of users wanting to make new friends</li><li>!friends !join <bio> will add you to the list or update your bio, "bio" is up to 250 characters of words describing yourself. Ex. !friends !join male, Cuban, tech, free software, music</li><li>!friends !leave command will remove you from the DeltaFriends list</li></ul>Ex. !friends !join male,tech,free software,rock music.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!friends'

    NOSCRIPT = 'You need a browser with JavaScript support for this page to work correctly.'
    JOIN_BTN = 'Join/Update'
    LEAVE_BTN = 'Leave'
    LIST_BTN = 'Users List'
    PROFILE_HEADER = 'Profile'
    BIO = 'Bio'
    WRITE = 'Write'
    MAX_BIO_LEN = 250
    USER_ADDED = 'You are now in the DeltaFriends list'
    USER_REMOVED = 'You was removed from the DeltaFriends list'
    USER_NOT_FOUND = 'You are NOT in the DeltaFriends list'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.conn = sqlite3.connect(os.path.join(cls.ctx.basedir, 'deltafriends.db'))
        with cls.conn:
            cls.conn.execute('''CREATE TABLE IF NOT EXISTS deltafriends (addr TEXT NOT NULL, bio TEXT, PRIMARY KEY(addr))''')
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando !friends, para más información utilice !friends !help. Ej. !friends !join chico, música, tecnología, series, buscando amigos.'
        #     cls.USER_ADDED = 'Ahora estás en la lista de DeltaFriends'
        #     cls.USER_REMOVED = 'Fuiste eliminado de la lista de DeltaFriends'
        #     cls.USER_NOT_FOUND = 'No estás en la lista de DeltaFriends'
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
        for cmd,action in [('!join', cls.join_cmd), ('!leave', cls.leave_cmd),
                           ('!list', cls.list_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                action(msg, arg)
                break
        else:
            if not req:
                addr = msg.get_sender_contact().addr
                bio = cls.conn.execute('SELECT bio FROM deltafriends WHERE addr=?',(addr,)).fetchone()
                if bio is None:
                    bio = ""
                else:
                    bio = bio[0]
                html = cls.env.get_template('index.html').render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr, bio=bio)
                with open(cls.TEMP_FILE, 'w') as fd:
                    fd.write(html)
                chat = cls.ctx.acc.create_chat_by_message(msg)
                chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True

    @classmethod
    def list_cmd(cls, msg, *args):
        friends = [{'addr':addr, 'bio':bio}
                   for addr,bio in cls.conn.execute('SELECT * FROM deltafriends ORDER BY addr').fetchall()]
        html = cls.env.get_template('list.html').render(plugin=cls, friends=friends)
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(html)
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')

    @classmethod
    def join_cmd(cls, msg, text):
        addr = msg.get_sender_contact().addr
        text = ' '.join(text.split())
        if len(text) > cls.MAX_BIO_LEN:
            text = text[:cls.MAX_BIO_LEN] + '...'
        with cls.conn:
            cls.conn.execute('INSERT OR REPLACE INTO deltafriends VALUES (?, ?)', (addr, text))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(cls.USER_ADDED)

    @classmethod
    def leave_cmd(cls, msg, *args):
        addr = msg.get_sender_contact().addr
        with cls.conn:
            rowcount = cls.conn.execute('DELETE FROM deltafriends WHERE addr=?', (addr,)).rowcount
        if rowcount == 1:
            return cls.USER_REMOVED
        else:
            return cls.USER_NOT_FOUND

    # @classmethod
    # def search_cmd(cls, _, text):
    #     results = ''
    #     get_desc = lambda d: d if d else cls.NO_DESC
    #     t = re.compile(text, re.IGNORECASE)
    #     for addr,desc in cls.conn.execute('SELECT * FROM deltafriends ORDER BY addr'):
    #         desc = get_desc(desc)
    #         if t.findall(desc) or t.findall(addr):
    #             results += '🔘 {}: {}\n\n'.format(addr, desc)
    #     return cls.SEARCH_RESULTS.format(text)+results

    # @classmethod
    # def help_cmd(cls, *args):
    #     return '\n\n'.join(['DeltaFriends:\n', cls.hcmd_list, cls.hcmd_join.format(cls.MAX_BIO_LEN),
    #                         cls.hcmd_leave])
