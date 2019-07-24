# -*- coding: utf-8 -*-
from  urllib.parse import quote_plus
import gettext
import os
import random
import string
import sqlite3

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin
import deltachat as dc


PUBLIC = 1
PRIVATE = 0


class GroupMaster(Plugin):

    name = 'GroupMaster'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!group!list'

    MAX_TOPIC_SIZE = 250
    DELTA_URL = 'http://delta.chat/group/'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.conn = sqlite3.connect(os.path.join(cls.ctx.basedir, 'groupmaster.db'))
        with cls.conn:
            cls.conn.execute('''CREATE TABLE IF NOT EXISTS groups (id INTEGER NOT NULL, pid TEXT NOT NULL, topic TEXT, status INTEGER,  PRIMARY KEY(id))''')
        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        try:
            lang = gettext.translation('simplebot_groupmaster', localedir=localedir,
                                       languages=[ctx.locale])
        except OSError:
            lang = gettext.translation('simplebot_groupmaster', localedir=localedir,
                                       languages=['en'])
        lang.install()
        cls.description = _('plugin-description')
        cls.long_description = _('plugin-long-description').format(cls.MAX_TOPIC_SIZE)
        cls.LIST_BTN = _('list_btn')
        cls.JOIN_BTN = _('join_btn')
        cls.LEAVE_BTN = _('leave_btn')
        
    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!group', msg.text)
        if arg is None:
            return False
        req = arg
        for cmd,action in [('!id', cls.id_cmd), ('!list', cls.list_cmd), ('!join', cls.join_cmd),
                           ('!leave', cls.leave_cmd), ('!public', cls.public_cmd), ('!private', cls.private_cmd),
                           ('!topic', cls.topic_cmd), ('!add', cls.add_cmd), ('!remove', cls.remove_cmd),
                           ('!msg', cls.msg_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                action(msg, arg)
                break
        else:
            template = cls.env.get_template('index.html')
            with open(cls.TEMP_FILE, 'w') as fd:
                fd.write(template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr))
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        return True

    @classmethod
    def get_info(cls, gid):
        info = cls.conn.execute('SELECT pid,topic,status FROM groups WHERE id=?', (gid,)).fetchone()
        if info is None:
            pid = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                          for i in range(10))
            info = (pid, '', PRIVATE)
            with cls.conn:
                cls.conn.execute('INSERT INTO groups VALUES (?,?,?,?)', (gid, info[0], info[1], info[2]))
        return info

    @classmethod
    def get_groups(cls, public_only=False):
        me = cls.ctx.acc.get_self_contact()
        groups = []
        for chat in cls.ctx.acc.get_chats():
            if chat.get_type() in (dc.const.DC_CHAT_TYPE_GROUP,
                                   dc.const.DC_CHAT_TYPE_VERIFIED_GROUP):
                if me not in chat.get_contacts():
                    with cls.conn:
                        cls.conn.execute('DELETE FROM groups WHERE id=?', (chat.id,))
                    chat.delete()
                else:
                    if public_only and cls.get_info(chat.id)[2] != PUBLIC:
                        continue
                    groups.append(chat)
        return groups

    @classmethod
    def id_cmd(cls, msg, _):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if msg.chat.get_type() not in (dc.const.DC_CHAT_TYPE_GROUP,
                                       dc.const.DC_CHAT_TYPE_VERIFIED_GROUP):
            text = _('not_a_group')
        else:
            pid, topic, status = cls.get_info(msg.chat.id)
            if status == PUBLIC:
                status = _('group_status').format(_('group_public'))
                gid = '{}{}'.format(cls.DELTA_URL, msg.chat.id)
            else:
                status = _('group_status').format(_('group_private'))
                gid = '{}{}-{}'.format(cls.DELTA_URL, pid, msg.chat.id)
            text = status+'\nID: {}'.format(gid)
        chat.send_text(text)

    @classmethod
    def public_cmd(cls, msg, _):
        pid, topic, status = cls.get_info(msg.chat.id)
        if status != PUBLIC:
            with cls.conn:
                cls.conn.execute('REPLACE INTO groups VALUES (?,?,?,?)', (msg.chat.id, pid, topic, PUBLIC))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(_('group_status').format(_('group_public')))

    @classmethod
    def private_cmd(cls, msg, _):
        pid, topic, status = cls.get_info(msg.chat.id)
        if status != PRIVATE:
            with cls.conn:
                cls.conn.execute('REPLACE INTO groups VALUES (?,?,?,?)', (msg.chat.id, pid, topic, PRIVATE))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(_('group_status').format(_('group_private')))

    @classmethod
    def topic_cmd(cls, msg, new_topic):
        pid, topic, status = cls.get_info(msg.chat.id)
        new_topic = ' '.join(new_topic.split())
        if new_topic:
            if len(new_topic) > 250:
                new_topic = new_topic[:250]+'...'
            topic = new_topic
            with cls.conn:
                cls.conn.execute('REPLACE INTO groups VALUES (?,?,?,?)', (msg.chat.id, pid, topic, status))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(_('topic').format(topic))

    @classmethod
    def join_cmd(cls, msg, arg):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        try:
            gid = arg.strip(cls.DELTA_URL).split('-')
            pid = ''
            if len(gid) == 2:
                pid = gid[0] 
            gid = int(gid.pop())
            for g in cls.get_groups():
                if g.id == gid:
                    pid1, topic, status = cls.get_info(g.id)
                    if status == PUBLIC or pid1 == pid:
                        g.add_contact(msg.get_sender_contact())
                        chat.send_text(_('added_to_group').format(g.get_name(), g.id, topic))
                        return
                    raise ValueError
        except ValueError:
            gid = arg
        chat.send_text(_('unknow_group').format(gid))

    @classmethod
    def leave_cmd(cls, msg, arg):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        try:
            gid = int(arg.strip(cls.DELTA_URL).split('-').pop())
            for g in cls.get_groups():
                if g.id == gid and msg.get_sender_contact() in g.get_contacts():
                    g.remove_contact(msg.get_sender_contact())
                    chat.send_text(_('removed_from_group').format(g.get_name(), g.id))
                    return
        except ValueError:
            gid = arg
        chat.send_text(_('unknow_group').format(gid))

    @classmethod
    def add_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            gid = int(arg[:i].strip(cls.DELTA_URL).split('-').pop())
            addrs = arg[i:].strip().split(',')
            if i < 0:
                raise ValueError
        except ValueError:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(cls.description+'\n\n'+cls.long_description)
            return
        for g in cls.get_groups():
            if g.id == gid and msg.get_sender_contact() in g.get_contacts():
                topic = cls.get_info(g.id)[1]
                sender = msg.get_sender_contact().addr
                for addr in addrs:
                    c = cls.ctx.acc.create_contact(addr.strip())
                    g.add_contact(c)
                    chat = cls.ctx.acc.create_chat_by_contact(c)
                    chat.send_text(_('added_to_group_by').format(g.get_name(), g.id, sender, topic))
                break

    @classmethod
    def remove_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            gid = int(arg[:i].strip(cls.DELTA_URL).split('-').pop())
            addr = arg[i:].strip()
            if i < 0:
                raise ValueError
        except ValueError:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(cls.description+'\n\n'+cls.long_description)
            return
        for g in cls.get_groups():
            if g.id == gid and msg.get_sender_contact() in g.get_contacts():
                c = [c for c in cls.ctx.acc.get_contacts(addr) if c.addr == addr][0]  # TODO: error if addr not in group
                g.remove_contact(c)
                sender = msg.get_sender_contact().addr
                chat = cls.ctx.acc.create_chat_by_contact(c)
                chat.send_text(_('removed_from_group_by').format(g.get_name(), g.id, sender))
                break

    @classmethod
    def msg_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i].strip(cls.DELTA_URL).split('-').pop())
            text = arg[i:].strip()
            if i < 0 or not msg:
                raise ValueError
        except ValueError:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(cls.description+'\n\n'+cls.long_description)
            return
        sender = msg.get_sender_contact()
        for g in cls.get_groups():
            if g.id == group_id and sender in g.get_contacts():
                g.send_text('{}:\n{}'.format(sender.addr, text))
                break

    @classmethod
    def list_cmd(cls, msg, arg):
        groups = cls.get_groups(public_only=True)
        groups.sort(key=lambda g: g.get_name())
        for i,g in enumerate(groups):
            topic = cls.get_info(g.id)[1]
            gid = quote_plus('{}{}'.format(cls.DELTA_URL, g.id))
            groups[i] = (g.get_name(), topic, gid, len(g.get_contacts()))
        template = cls.env.get_template('list.html')
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr, groups=groups))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')
