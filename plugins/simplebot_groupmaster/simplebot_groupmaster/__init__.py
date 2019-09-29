# -*- coding: utf-8 -*-
from enum import IntEnum
from urllib.parse import quote_plus
import gettext
import os
import random
import string
import sqlite3

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin, Mode, PluginFilter, PluginCommand
import deltachat as dc


GROUP_URL = 'http://delta.chat/group/'
MGROUP_URL = 'http://delta.chat/mega-group/'


class Status(IntEnum):
    PRIVATE = 0
    PUBLIC = 1


class GroupMaster(Plugin):

    name = 'GroupMaster'
    version = '0.2.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'groupmaster.db'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_groupmaster', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _(
            'Extends the capabilities of DeltaChat groups.')
        cls.filters = [PluginFilter(cls.process_messages)]
        cls.bot.add_filters(cls.filters)
        cls.commands = [
            PluginCommand('/group/mega', [], _(
                'Convert the group where it is sent in a mega-group.'), cls.mega_cmd),
            PluginCommand('/nick', ['[nick]'], _(
                'Show your current nick or set your nick to be shown in mega-groups.'), cls.nick_cmd),
            PluginCommand(
                '/group/id', [], _('Show the id of the group (or mega-group) where it is sent.'), cls.id_cmd),
            PluginCommand(
                '/group/list', [], _('Show the list of public groups and mega-groups.'), cls.list_cmd),
            PluginCommand(
                '/group/me', [], _('Show the list of public groups/mega-groups you are in.'), cls.me_cmd),
            PluginCommand('/group/members', [], _(
                'Show the list of members in the mega-group it is sent.'), cls.members_cmd),
            PluginCommand('/group/join', ['<id>'], _(
                'Joins you to the group (or mega-group) with the given id.'), cls.join_cmd),
            PluginCommand(
                '/group/public', [], _('Send it in a group (or mega-group) to make it public.'), cls.public_cmd),
            PluginCommand('/group/private', [], _(
                'Send it in a group (or mega-group) to make it private.'), cls.private_cmd),
            PluginCommand('/group/topic', ['[topic]'], _(
                'Send it in a group (or mega-group) to show the current topic or replace it.'), cls.topic_cmd),
            PluginCommand('/group/remove', ['<id>', '<addr>'], _(
                'Remove the member with the given address from the group (or mega-group) with the given id.'), cls.remove_cmd)]
        cls.bot.add_commands(cls.commands)

        cls.LIST_BTN = _('Groups List')
        cls.JOIN_BTN = _('Join')

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.db.close()

    @classmethod
    def get_nick(cls, addr):
        r = cls.db.execute(
            'SELECT nick from nicks WHERE addr=?', (addr,)).fetchone()
        if r:
            return r[0]
        else:
            return addr

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        mg = cls.get_mgroup(chat.id)
        if mg:
            if ctx.msg.view_type != dc.const.DC_MSG_TEXT:
                nick = cls.get_nick(ctx.msg.get_sender_contact().addr)
                for g in cls.get_mchats(mg['id']):
                    if g.id != chat.id:
                        g.send_text('{}:\n{}'.format(nick, ctx.text))
            else:
                chat.send_text(
                    _('Only text messages are supported in mega-groups'))
            ctx.processed = True

    @classmethod
    def generate_pid(cls):
        return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(10))

    @classmethod
    def get_mchats(cls, mgid):
        me = cls.bot.get_contact()
        chats = []
        invalid_chats = []
        old_chats = (cls.bot.get_chat(r[0]) for r in cls.db.execute(
            'SELECT id FROM mchats WHERE mgroup=?', (mgid,)))
        for chat in old_chats:
            contacts = chat.get_contacts()
            if me not in contacts or len(contacts) < 2:
                invalid_chats.append(chat)
            else:
                chats.append(chat)
        for chat in invalid_chats:
            cls.db.execute('DELETE FROM mchats WHERE id=?', (chat.id,))
            chat.remove_contact(me)
        if not chats:
            cls.db.execute('DELETE FROM mgroups WHERE id=?', (mgid,))
        return chats

    @classmethod
    def get_mgroup(cls, gid):
        r = cls.db.execute(
            'SELECT mgroup FROM mchats WHERE id=?', (gid,)).fetchone()
        if r:
            return cls.db.execute('SELECT * FROM mgroups WHERE id=?', (r[0],)).fetchone()
        return None

    @classmethod
    def get_info(cls, gid):
        info = cls.db.execute(
            'SELECT pid,topic,status FROM groups WHERE id=?', (gid,)).fetchone()
        if info is None:
            info = (cls.generate_pid(), '', Status.PRIVATE)
            cls.db.execute(
                'INSERT INTO groups VALUES (?,?,?,?)', (gid, *info))
        else:
            info = tuple(info)
        return info

    @classmethod
    def get_groups(cls, public_only=False):
        me = cls.bot.get_contact()
        groups = []
        for chat in cls.bot.get_chats():
            if cls.bot.is_group(chat):
                if me in chat.get_contacts():
                    if public_only and cls.get_info(chat.id)[2] != Status.PUBLIC:
                        continue
                    groups.append(chat)
        return groups

    @classmethod
    def mega_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if cls.get_mgroup(chat.id):
            chat.send_text(_('This is already a mega-group'))
            return

        me = cls.bot.get_contact()
        sender = ctx.msg.get_sender_contact()
        name = chat.get_name()
        chats = []
        for contact in chat.get_contacts():
            if contact in (me, sender):
                continue
            try:
                chat.remove_contact(contact)
            except ValueError as ex:
                cls.bot.logger.exception(ex)
            chats.append(cls.bot.create_group(name, [contact]))
        pid, topic, status = cls.get_info(chat.id)
        try:
            chat.remove_contact(sender)
        except ValueError as ex:
            cls.bot.logger.exception(ex)
        chats.append(cls.bot.create_group(name, [sender]))
        try:
            chat.remove_contact(me)
        except ValueError as ex:
            cls.bot.logger.exception(ex)
        mgid = cls.db.execute('INSERT INTO mgroups VALUES(?,?,?,?,?)',
                              (None, pid, name, topic, status)).lastrowid
        for g in chats:
            cls.db.execute('INSERT INTO mchats VALUES (?,?)', (g.id, mgid))
            g.send_text(_('Mega-group created'))

    @classmethod
    def nick_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        addr = ctx.msg.get_sender_contact().addr
        new_nick = ' '.join(ctx.text.split())
        if new_nick:
            if new_nick == addr:
                cls.db.execute('DELETE FROM nicks WHERE addr=?', (addr,))
                text = _('** Nick: {}').format(addr)
            elif '@' in new_nick or ':' in new_nick or len(new_nick) > 30:
                text = _(
                    '** Invalid nick, "@" and ":" not allowed, and nick should be less than 30 characters')
            elif cls.db.execute('SELECT * FROM nicks WHERE nick=?', (new_nick,)).fetchone():
                text = _('** Nick already taken')
            else:
                text = _('** Nick: {}').format(new_nick)
                cls.db.execute(
                    'INSERT OR REPLACE INTO nicks VALUES (?,?)', (addr, new_nick))
        else:
            text = _('** Nick: {}').format(cls.get_nick(addr))
        chat.send_text(text)

    @classmethod
    def id_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if cls.bot.is_group(chat):
            mg = cls.get_mgroup(chat.id)
            if mg:
                if mg['status'] == Status.PUBLIC:
                    status = _('Group status: {}').format(_('Public'))
                    gid = '{}{}'.format(MGROUP_URL, mg['id'])
                else:
                    status = _('Group status: {}').format(_('Private'))
                    gid = '{}{}-{}'.format(MGROUP_URL, mg['pid'], mg['id'])
            else:
                url = GROUP_URL
                pid, topic, status = cls.get_info(chat.id)
                if status == Status.PUBLIC:
                    status = _('Group status: {}').format(_('Public'))
                    gid = '{}{}'.format(url, chat.id)
                else:
                    status = _('Group status: {}').format(_('Private'))
                    gid = '{}{}-{}'.format(url, pid, chat.id)
            text = '{}\nID: {}'.format(status, gid)
            chat.send_text(text)
        else:
            chat.send_text(_('This is NOT a group'))

    @classmethod
    def public_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        addr = ctx.msg.get_sender_contact().addr
        mg = cls.get_mgroup(chat.id)
        if mg:
            if mg['status'] != Status.PUBLIC:
                cls.db.execute(
                    'UPDATE mgroups SET status=? WHERE id=?', (Status.PUBLIC, mg['id'],))
                text = _('** {} changed group status to: {}').format(
                    cls.get_nick(addr), _('Public'))
                for chat in cls.get_mchats(mg['id']):
                    chat.send_text(text)
        else:
            if cls.get_info(chat.id)[2] != Status.PUBLIC:
                cls.db.execute(
                    'UPDATE groups SET status=? WHERE id=?', (Status.PUBLIC, chat.id))
                chat.send_text(
                    _('** {} changed group status to: {}').format(addr, _('Public')))

    @classmethod
    def private_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        addr = ctx.msg.get_sender_contact().addr
        mg = cls.get_mgroup(chat.id)
        if mg:
            if mg['status'] != Status.PRIVATE:
                cls.db.execute(
                    'UPDATE mgroups SET status=? WHERE id=?', (Status.PRIVATE, mg['id'],))
                text = _('** {} changed group status to: {}').format(
                    cls.get_nick(addr), _('Private'))
                for chat in cls.get_mchats(mg['id']):
                    chat.send_text(text)
        else:
            if cls.get_info(chat.id)[2] != Status.PRIVATE:
                cls.db.execute(
                    'UPDATE groups SET status=? WHERE id=?', (Status.PRIVATE, chat.id))
                chat.send_text(
                    _('** {} changed group status to: {}').format(addr, _('Private')))

    @classmethod
    def topic_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        mg = cls.get_mgroup(chat.id)
        new_topic = ' '.join(ctx.text.split())
        if new_topic:
            if len(new_topic) > 250:
                new_topic = new_topic[:250]+'...'
            addr = ctx.msg.get_sender_contact().addr
            banner = _('** {} changed topic to:\n{}')
            if mg:
                cls.db.execute(
                    'UPDATE mgroups SET topic=? WHERE id=?', (new_topic, mg['id']))
                text = banner.format(cls.get_nick(addr), new_topic)
                for chat in cls.get_mchats(mg['id']):
                    chat.send_text(text)
            else:
                cls.db.execute(
                    'UPDATE groups SET topic=? WHERE id=?', (new_topic, chat.id))
                chat.send_text(banner.format(addr, new_topic))
        else:
            topic = mg['topic'] if mg else cls.get_info(chat.id)[1]
            chat.send_text(_('Topic:\n{}').format(topic))

    @classmethod
    def join_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        sender = ctx.msg.get_sender_contact()
        try:
            if ctx.text.startswith(MGROUP_URL):
                is_mgroup = True
                gid = ctx.text.lstrip(MGROUP_URL).split('-')
            elif ctx.text.startswith(GROUP_URL):
                is_mgroup = False
                gid = ctx.text.lstrip(GROUP_URL).split('-')
            else:
                raise ValueError('Invalid Group ID')
            pid = ''
            if len(gid) == 2:
                pid = gid[0]
            gid = int(gid[-1])
            banner = _('Added to {}\n(ID:{})\n\nTopic:\n{}')
            if is_mgroup:
                mg = cls.db.execute(
                    'SELECT * FROM mgroups WHERE id=?', (gid,)).fetchone()
                if mg and (mg['status'] == Status.PUBLIC or mg['pid'] == pid):
                    for g in cls.get_mchats(mg['id']):
                        if sender in g.get_contacts():
                            chat.send_text(
                                _('You are already a member of that group'))
                            return
                    g = cls.bot.create_group(
                        mg['name'], [sender])
                    cls.db.execute(
                        'INSERT INTO mchats VALUES (?,?)', (g.id, mg['id']))
                    text = _(
                        '** {} joined the group').format(cls.get_nick(sender.addr))
                    for chat in cls.get_mchats(mg['id']):
                        if chat.id != g.id:
                            chat.send_text(text)
                    g.send_text(banner.format(
                        mg['name'], ctx.text, mg['topic']))
                    return
            else:
                for g in cls.get_groups():
                    if g.id == gid:
                        pid1, topic, status = cls.get_info(gid)
                        if status == Status.PUBLIC or pid1 == pid:
                            if sender in g.get_contacts():
                                chat.send_text(
                                    _('You are already a member of that group'))
                            else:
                                g.add_contact(sender)
                                chat.send_text(banner.format(
                                    g.get_name(), ctx.text, topic))
                            return
                        break
        except (ValueError, IndexError) as err:
            cls.bot.logger.exception(err)
        chat.send_text(_('Unknow group ID: {}').format(ctx.text))

    @classmethod
    def remove_cmd(cls, ctx):
        sender = ctx.msg.get_sender_contact()
        try:
            gid, addr = ctx.text.split(maxsplit=1)
            addr = addr.rstrip()
            if addr == cls.bot.get_address():
                raise ValueError('Tried to remove bot from mega-group')
            if gid.startswith(MGROUP_URL):
                _mgid = gid.lstrip(MGROUP_URL).split('-')[-1]
                mgroup = cls.db.execute(
                    'SELECT * FROM mgroups WHERE id=?', (_mgid,)).fetchone()
                if not mgroup:
                    raise ValueError('Wrong syntax')
            elif gid.startswith(GROUP_URL):
                mgroup = None
                gid = int(gid.lstrip(GROUP_URL).split('-')[-1])
                for g in cls.get_groups():
                    if g.id == gid:
                        group = g
                        break
                else:
                    raise ValueError('Wrong syntax')
            else:
                raise ValueError('Wrong syntax')
            if '@' not in addr and not mgroup:
                raise ValueError('Invalid email address')
        except (ValueError, IndexError) as err:
            cls.bot.get_chat(sender).send_text(_('Wrong syntax'))
            return

        banner = _('Removed from {} by {}')
        if mgroup:
            if '@' not in addr:
                r = cls.db.execute(
                    'SELECT addr FROM nicks WHERE nick=?', (addr,)).fetchone()
                if not r:
                    cls.bot.get_chat(sender).send_text(
                        _('Unknow user: {}').format(addr))
                else:
                    addr = r[0]
            contact = cls.bot.get_contact(addr)
            cgroup = None
            is_member = False
            for g in cls.get_mchats(mgroup['id']):
                contacts = g.get_contacts()
                if contact in contacts:
                    cgroup = g
                if sender in contacts:
                    is_member = True
            if is_member and cgroup:
                cgroup.remove_contact(contact)
                sender_nick = cls.get_nick(sender.addr)
                nick = cls.get_nick(addr)
                cls.bot.get_chat(contact).send_text(
                    banner.format(mgroup['name'], sender_nick))
                text = _('** {} removed by {}').format(nick, sender_nick)
                for chat in cls.get_mchats(mgroup['id']):
                    chat.send_text(text)
        else:
            contact = cls.bot.get_contact(addr)
            contacts = group.get_contacts()
            if sender in contacts and contact in contacts:
                group.remove_contact(contact)
                chat = cls.bot.get_chat(contact)
                chat.send_text(banner.format(group.get_name(), sender.addr))

    @classmethod
    def list_cmd(cls, ctx):
        groups = cls.get_groups(public_only=True)
        for i, g in enumerate(groups):
            topic = cls.get_info(g.id)[1]
            groups[i] = [g.get_name(), topic, '{}{}'.format(
                GROUP_URL, g.id), len(g.get_contacts())]
        mgroups = []
        for mg in cls.db.execute('SELECT * FROM mgroups WHERE status=?', (Status.PUBLIC,)):
            count = sum(map(lambda g: len(g.get_contacts())-1,
                            cls.get_mchats(mg['id'])))
            if count == 0:
                continue
            mgroups.append(
                [mg['name'], mg['topic'], '{}{}'.format(MGROUP_URL, mg['id']), count])
        groups.extend(mgroups)
        chat = cls.bot.get_chat(ctx.msg)
        gcount = len(groups)
        if ctx.mode == Mode.TEXT:
            groups.sort(key=lambda g: g[-1])
            text = '{0} ({1}):\n\n'.format(cls.name, gcount)
            for g in groups:
                text += _('{0}:\n* {3} 👤\nTopic: {1}\nID: {2}\n\n').format(*g)
            chat.send_text(text)
        else:
            groups.sort(key=lambda g: g[-1], reverse=True)
            for i in range(gcount):
                groups[i][2] = quote_plus(groups[i][2])
            template = cls.env.get_template('list.html')
            html = template.render(
                plugin=cls, bot_addr=cls.bot.get_address(), groups=groups)
            cls.bot.send_html(chat, html, cls.name, ctx.mode)

    @classmethod
    def me_cmd(cls, ctx):
        sender = ctx.msg.get_sender_contact()
        groups = []
        for g in cls.get_groups(public_only=True):
            if sender in g.get_contacts():
                groups.append((g.get_name(), '{}{}'.format(GROUP_URL, g.id)))
        mgroups = []
        for mg in cls.db.execute('SELECT * FROM mgroups WHERE status=?', (Status.PUBLIC,)):
            for g in cls.get_mchats(mg['id']):
                if sender in g.get_contacts():
                    mgroups.append(
                        (mg['name'], '{}{}'.format(MGROUP_URL, mg['id'])))
                    break
        groups.extend(mgroups)

        text = ''
        for g in groups:
            text += _('{0}:\nID: {1}\n\n').format(*g)
        chat = cls.bot.get_chat(ctx.msg)
        chat.send_text(text)

    @classmethod
    def members_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        me = cls.bot.get_contact()
        mg = cls.get_mgroup(chat.id)
        if mg:
            text = '{}:\n\n'.format(mg['name'])
            count = 0
            for g in cls.get_mchats(mg['id']):
                for c in g.get_contacts():
                    if c != me:
                        text += '* {}\n'.format(cls.get_nick(c.addr))
                        count += 1
            text += '\n\n'
            text += _('Total: {}').format(count)
            chat.send_text(text)
        else:
            chat.send_text(_('This is NOT a mega-group'))


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.execute('''CREATE TABLE IF NOT EXISTS groups
                        (id INTEGER PRIMARY KEY,
                         pid TEXT NOT NULL,
                         topic TEXT,
                         status INTEGER)''')
        self.execute('''CREATE TABLE IF NOT EXISTS mgroups
                        (id INTEGER PRIMARY KEY,
                         pid TEXT NOT NULL,
                         name TEXT NOT NULL,
                         topic TEXT,
                         status INTEGER NOT NULL)''')
        self.execute('''CREATE TABLE IF NOT EXISTS mchats
                        (id INTEGER PRIMARY KEY,
                         mgroup INTEGER NOT NULL REFERENCES mgroups(id))''')
        self.execute('''CREATE TABLE IF NOT EXISTS nicks
                        (addr TEXT PRIMARY KEY,
                         nick TEXT NOT NULL)''')

    def execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def close(self):
        self.db.close()
