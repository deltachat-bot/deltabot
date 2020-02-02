# -*- coding: utf-8 -*-
from enum import IntEnum
from urllib.parse import quote_plus
import gettext
import os
import random
import re
import string
import sqlite3

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin, Mode, PluginFilter, PluginCommand


GROUP_URL = 'http://delta.chat/group/'
MGROUP_URL = 'http://delta.chat/mega-group/'
CHANNEL_URL = 'http://delta.chat/channel/'

nick_re = re.compile(r'[a-zA-Z0-9 ]{1,30}$')


def rmprefix(text, prefix):
    return text[text.startswith(prefix) and len(prefix):]


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
                'Show your current nick or set your nick to be shown in mega-groups or channels.'), cls.nick_cmd),
            PluginCommand(
                '/group/id', [], _('Show the id of the group, mega-group or channel where it is sent.'), cls.id_cmd),
            PluginCommand(
                '/group/list', [], _('Show the list of public groups, mega-groups and channels.'), cls.list_cmd),
            PluginCommand(
                '/group/me', [], _('Show the list of public groups,mega-groups and channels you are in.'), cls.me_cmd),
            PluginCommand('/group/members', [], _(
                'Show the list of members in the mega-group it is sent.'), cls.members_cmd),
            PluginCommand('/group/join', ['<id>'], _(
                'Joins you to the group, mega-group or channel with the given id.'), cls.join_cmd),
            PluginCommand(
                '/group/public', [], _('Send it in a group (or mega-group) to make it public.'), cls.public_cmd),
            PluginCommand('/group/private', [], _(
                'Send it in a group (or mega-group) to make it private.'), cls.private_cmd),
            PluginCommand('/group/topic', ['[topic]'], _(
                'Send it in a group, mega-group or channel to show the current topic or replace it.'), cls.topic_cmd),
            PluginCommand('/group/name', ['<name>'], _(
                'Send it in a mega-group to change its name.'), cls.name_cmd),
            PluginCommand('/group/image', [], _(
                'Change the mega-group image, you must attach an image to the message sending this command'), cls.image_cmd),
            PluginCommand('/group/remove', ['<id>', '[addr]'], _(
                'Remove the member with the given address from the group (or mega-group) with the given id. If no address is provided, removes yourself'), cls.remove_cmd),
            PluginCommand('/channel', ['<name>'], _(
                'Create a new channel with the given name'), cls.channel_cmd),
            PluginCommand('/channel/image', [], _(
                'Change the channel image, you must attach an image to the message sending this command. Only channel operator can change the channel image'), cls.cimage_cmd), ]
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
            i = 1
            while True:
                nick = 'User{}'.format(i)
                r = cls.db.execute(
                    'SELECT nick FROM nicks WHERE nick=?', (nick,)).fetchone()
                if not r:
                    cls.db.execute(
                        'INSERT OR REPLACE INTO nicks VALUES (?,?)', (addr, nick))
                    break
                i += 1
            return nick

    @classmethod
    def process_messages(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        mg = cls.get_mgroup(chat.id)
        sender = ctx.msg.get_sender_contact()
        if mg:
            ctx.processed = True
            contacts = chat.get_contacts()
            nick = cls.get_nick(sender.addr)
            if sender not in contacts:
                return
            ctx.text = '{}:\n{}'.format(
                nick, ctx.text) if ctx.text else nick
            if ctx.msg.filename:
                if os.path.getsize(ctx.msg.filename) <= 61440:  # <=60KB
                    for g in cls.get_mchats(mg['id']):
                        if g.id != chat.id:
                            cls.bot.send_file(g, ctx.msg.filename, ctx.text)
                else:
                    chat.send_text(
                        _('Message is too big, only up to 60KB are allowed'))
            else:
                for g in cls.get_mchats(mg['id']):
                    if g.id != chat.id:
                        g.send_text(ctx.text)
            return
        ch = cls.get_channel(chat.id)
        if ch and ch['admin'] == chat.id:
            ctx.processed = True
            nick = cls.get_nick(sender.addr)
            if ctx.msg.filename:
                if os.path.getsize(ctx.msg.filename) <= 102400:
                    ctx.text = '{}:\n{}'.format(
                        nick, ctx.text) if ctx.text else nick
                    for g in cls.get_cchats(ch['id']):
                        cls.bot.send_file(g, ctx.msg.filename, ctx.text)
                else:
                    chat.send_text(
                        _('Message is too big, only up to 100KB are allowed'))
            else:
                contacts = chat.get_contacts()
                if sender not in contacts:
                    return
                for g in cls.get_cchats(ch['id']):
                    g.send_text('{}:\n{}'.format(nick, ctx.text))
        elif ch:
            ctx.processed = True
            contacts = chat.get_contacts()
            if sender in contacts:  # if user isn't leaving the group
                chat.send_text(_('Only channel operators can do that.'))

    @classmethod
    def generate_pid(cls):
        return ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits) for i in range(10))

    @classmethod
    def get_mchats(cls, mgid):
        me = cls.bot.get_contact()
        chats = []
        invalid_chats = []
        old_chats = cls.db.execute(
            'SELECT id FROM mchats WHERE mgroup=?', (mgid,))
        for r in old_chats:
            chat = cls.bot.get_chat(r[0])
            if chat is None:
                cls.db.execute('DELETE FROM mchats WHERE id=?', (r[0],))
                continue
            contacts = chat.get_contacts()
            if me not in contacts or len(contacts) == 1:
                invalid_chats.append(chat)
            else:
                chats.append(chat)
        for chat in invalid_chats:
            cls.db.execute('DELETE FROM mchats WHERE id=?', (chat.id,))
            chat.remove_contact(me)
        if not chats:
            cls.db.execute('DELETE FROM mgroups WHERE id=?', (mgid,))
            cls.db.execute('DELETE FROM mg_images WHERE mgroup=?', (mgid,))
        return chats

    @classmethod
    def get_cchats(cls, cgid):
        me = cls.bot.get_contact()
        chats = []
        invalid_chats = []
        old_chats = []
        for r in cls.db.execute('SELECT id FROM cchats WHERE channel=?', (cgid,)):
            c = cls.bot.get_chat(r[0])
            if c is None:
                cls.db.execute('DELETE FROM cchats WHERE id=?', (r[0],))
            else:
                old_chats.append(c)
        admin = cls.db.execute(
            'SELECT admin FROM channels WHERE id=?', (cgid,)).fetchone()[0]
        admin = cls.bot.get_chat(admin)
        if admin is None:
            admins = []
        else:
            admins = admin.get_contacts()
        if me not in admins or len(admins) == 1:
            invalid_chats = old_chats
            cls.db.execute('DELETE FROM channels WHERE id=?', (cgid,))
            cls.db.execute(
                'DELETE FROM channel_images WHERE channel=?', (cgid,))
        else:
            for chat in old_chats:
                contacts = chat.get_contacts()
                if me not in contacts or len(contacts) == 1:
                    invalid_chats.append(chat)
                else:
                    chats.append(chat)
        for chat in invalid_chats:
            cls.db.execute('DELETE FROM cchats WHERE id=?', (chat.id,))
            chat.remove_contact(me)
        return chats

    @classmethod
    def get_mgroup(cls, gid):
        r = cls.db.execute(
            'SELECT mgroup FROM mchats WHERE id=?', (gid,)).fetchone()
        if r:
            return cls.db.execute('SELECT * FROM mgroups WHERE id=?', (r[0],)).fetchone()
        return None

    @classmethod
    def get_channel(cls, gid):
        r = cls.db.execute(
            'SELECT channel FROM cchats WHERE id=?', (gid,)).fetchone()
        if r:
            return cls.db.execute(
                'SELECT * FROM channels WHERE id=?', (r[0],)).fetchone()
        return cls.db.execute(
            'SELECT * FROM channels WHERE admin=?', (gid,)).fetchone()

    @classmethod
    def get_info(cls, gid, create=False):
        info = cls.db.execute(
            'SELECT pid,topic,status FROM groups WHERE id=?', (gid,)).fetchone()
        if info is None:
            info = (cls.generate_pid(), '', Status.PRIVATE)
            if create:
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
            if new_nick != addr and not nick_re.match(new_nick):
                text = _(
                    '** Invalid nick, only letters, numbers and space are allowed, and nick should be less than 30 characters')
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
                text = '{}\nID: {}'.format(status, gid)
                chat.send_text(text)
                return
            ch = cls.get_channel(chat.id)
            if ch:
                if ch['status'] == Status.PUBLIC:
                    status = _('Channel status: {}').format(_('Public'))
                    gid = '{}{}'.format(CHANNEL_URL, ch['id'])
                else:
                    status = _('Channel status: {}').format(_('Private'))
                    gid = '{}{}-{}'.format(CHANNEL_URL, ch['pid'], ch['id'])
                text = '{}\nID: {}'.format(status, gid)
                chat.send_text(text)
            else:
                url = GROUP_URL
                pid, topic, status = cls.get_info(chat.id, create=True)
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
            ch = cls.get_channel(chat.id)
            if not ch:
                if cls.get_info(chat.id, create=True)[2] != Status.PUBLIC:
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
            ch = cls.get_channel(chat.id)
            if not ch:
                if cls.get_info(chat.id, create=True)[2] != Status.PRIVATE:
                    cls.db.execute(
                        'UPDATE groups SET status=? WHERE id=?', (Status.PRIVATE, chat.id))
                    chat.send_text(
                        _('** {} changed group status to: {}').format(addr, _('Private')))

    @classmethod
    def topic_cmd(cls, ctx):
        new_topic = ' '.join(ctx.text.split())
        chat = cls.bot.get_chat(ctx.msg)
        mg = cls.get_mgroup(chat.id)
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
                ch = cls.get_channel(chat.id)
                if not ch:
                    cls.db.execute(
                        'UPDATE groups SET topic=? WHERE id=?', (new_topic, chat.id))
                    chat.send_text(banner.format(addr, new_topic))
                elif ch['admin'] == chat.id:
                    cls.db.execute(
                        'UPDATE channels SET topic=? WHERE id=?', (new_topic, ch['id']))
                    text = banner.format(cls.get_nick(addr), new_topic)
                    for chat in cls.get_cchats(ch['id']):
                        chat.send_text(text)
                else:
                    chat.send_text(_('Only channel operators can do that.'))
        else:
            if mg:
                topic = mg['topic']
            else:
                ch = cls.get_channel(chat.id)
                if ch:
                    topic = ch['topic']
                else:
                    topic = cls.get_info(chat.id)[1]
            chat.send_text(_('Topic:\n{}').format(topic))

    @classmethod
    def name_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        mg = cls.get_mgroup(chat.id)
        if mg and ctx.text:
            addr = ctx.msg.get_sender_contact().addr
            text = _('** {} changed group name').format(cls.get_nick(addr))
            cls.db.execute(
                'UPDATE mgroups SET name=? WHERE id=?', (ctx.text, mg['id']))
            for chat in cls.get_mchats(mg['id']):
                chat.set_name(ctx.text)
                chat.send_text(text)
        else:
            chat.send_text(_('Wrong syntax'))

    @classmethod
    def image_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if ctx.msg.filename and os.path.getsize(ctx.msg.filename) <= 102400:
            addr = ctx.msg.get_sender_contact().addr
            text = _('** {} changed group image').format(cls.get_nick(addr))
            extension = ctx.msg.filename.rsplit('.', maxsplit=1)[-1]
            with open(ctx.msg.filename, 'rb') as fd:
                img_blob = sqlite3.Binary(fd.read())

            mg = cls.get_mgroup(chat.id)
            if mg:
                cls.db.execute(
                    'INSERT OR REPLACE INTO mg_images VALUES(?,?,?)', (mg['id'], img_blob, extension))
                for g in cls.get_mchats(mg['id']):
                    g.set_profile_image(ctx.msg.filename)
                    if g.id != chat.id:
                        g.send_text(text)
                return
        chat.send_text(_('Wrong syntax'))

    @classmethod
    def cimage_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        if ctx.msg.filename and os.path.getsize(ctx.msg.filename) <= 102400:
            addr = ctx.msg.get_sender_contact().addr
            extension = ctx.msg.filename.rsplit('.', maxsplit=1)[-1]
            with open(ctx.msg.filename, 'rb') as fd:
                img_blob = sqlite3.Binary(fd.read())

            ch = cls.get_channel(chat.id)
            if ch and chat.id == ch['admin']:
                cls.db.execute(
                    'INSERT OR REPLACE INTO channel_images VALUES(?,?,?)', (ch['id'], img_blob, extension))
                for g in cls.get_cchats(ch['id']):
                    g.set_profile_image(ctx.msg.filename)
                chat.set_profile_image(ctx.msg.filename)
                return
        chat.send_text(_('Wrong syntax'))

    @classmethod
    def join_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        sender = ctx.msg.get_sender_contact()
        try:
            pid = ''
            banner = _('Added to {}\n(ID:{})\n\nTopic:\n{}')
            if ctx.text.startswith(MGROUP_URL):
                gid = rmprefix(ctx.text, MGROUP_URL).split('-')
                if len(gid) == 2:
                    pid = gid[0]
                gid = int(gid[-1])
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
                    img = cls.db.execute(
                        'SELECT image, extension FROM mg_images WHERE mgroup=?', (mg['id'],)).fetchone()
                    if img:
                        file_name = cls.bot.get_blobpath(
                            'mg-image.{}'.format(img['extension']))
                        with open(file_name, 'wb') as fd:
                            fd.write(img['image'])
                        g.set_profile_image(file_name)
                    g.send_text(banner.format(
                        mg['name'], ctx.text, mg['topic']))
                    return
            elif ctx.text.startswith(GROUP_URL):
                gid = rmprefix(ctx.text, GROUP_URL).split('-')
                if len(gid) == 2:
                    pid = gid[0]
                gid = int(gid[-1])
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
            elif ctx.text.startswith(CHANNEL_URL):
                gid = rmprefix(ctx.text, CHANNEL_URL).split('-')
                if len(gid) == 2:
                    pid = gid[0]
                gid = int(gid[-1])
                ch = cls.db.execute(
                    'SELECT * FROM channels WHERE id=?', (gid,)).fetchone()
                if ch and (ch['status'] == Status.PUBLIC or ch['pid'] == pid):
                    if sender in cls.bot.get_chat(ch['admin']).get_contacts():
                        chat.send_text(
                            _('You are already a member of that channel'))
                        return
                    for g in cls.get_cchats(ch['id']):
                        if sender in g.get_contacts():
                            chat.send_text(
                                _('You are already a member of that channel'))
                            return
                    g = cls.bot.create_group(ch['name'], [sender])
                    cls.db.execute(
                        'INSERT INTO cchats VALUES (?,?)', (g.id, ch['id']))
                    img = cls.db.execute(
                        'SELECT image, extension FROM channel_images WHERE channel=?', (ch['id'],)).fetchone()
                    if img:
                        file_name = cls.bot.get_blobpath(
                            'ch-image.{}'.format(img['extension']))
                        with open(file_name, 'wb') as fd:
                            fd.write(img['image'])
                        g.set_profile_image(file_name)
                    g.send_text(banner.format(
                        ch['name'], ctx.text, ch['topic']))
                    return
            else:
                raise ValueError('Invalid ID')
        except (ValueError, IndexError) as err:
            cls.bot.logger.exception(err)
        chat.send_text(_('Unknow ID: {}').format(ctx.text))

    @classmethod
    def remove_cmd(cls, ctx):
        sender = ctx.msg.get_sender_contact()
        banner = _('Removed from {} by {}')
        try:
            gid = ctx.text.split(maxsplit=1)
            if len(gid) == 2:
                gid, addr = gid
                if addr == cls.bot.get_address():
                    raise ValueError('Tried to remove bot from mega-group')
            else:
                gid = gid[0]
                addr = sender.addr
            if gid.startswith(MGROUP_URL):
                _mgid = rmprefix(gid, MGROUP_URL).split('-')[-1]
                mgroup = cls.db.execute(
                    'SELECT * FROM mgroups WHERE id=?', (_mgid,)).fetchone()
                if not mgroup:
                    raise ValueError('Wrong syntax')
                if '@' not in addr:
                    r = cls.db.execute(
                        'SELECT addr FROM nicks WHERE nick=?', (addr,)).fetchone()
                    if not r:
                        cls.bot.get_chat(sender).send_text(
                            _('Unknow user: {}').format(addr))
                        return
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
            elif gid.startswith(CHANNEL_URL):
                cgid = rmprefix(gid, CHANNEL_URL).split('-')[-1]
                channel = cls.db.execute(
                    'SELECT * FROM channels WHERE id=?', (cgid,)).fetchone()
                if not channel:
                    raise ValueError('Wrong syntax')
                for g in cls.get_cchats(channel['id']):
                    if sender in g.get_contacts():
                        g.remove_contact(sender)
                        break
                else:
                    g = cls.bot.get_chat(channel['admin'])
                    if sender in g.get_contacts():
                        g.remove_contact(sender)
            elif gid.startswith(GROUP_URL):
                gid = int(rmprefix(gid, GROUP_URL).split('-')[-1])
                for g in cls.get_groups():
                    if g.id == gid:
                        group = g
                        break
                else:
                    raise ValueError('Wrong syntax')
                contact = cls.bot.get_contact(addr)
                contacts = group.get_contacts()
                if sender in contacts and contact in contacts:
                    group.remove_contact(contact)
                    chat = cls.bot.get_chat(contact)
                    chat.send_text(banner.format(
                        group.get_name(), sender.addr))
            else:
                raise ValueError('Wrong syntax')
        except (ValueError, IndexError) as err:
            cls.bot.get_chat(sender).send_text(_('Wrong syntax'))
            return

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

        channels = []
        for ch in cls.db.execute('SELECT * FROM channels WHERE status=?', (Status.PUBLIC,)):
            count = sum(map(lambda g: len(g.get_contacts())-1,
                            cls.get_cchats(ch['id'])))
            channels.append(
                [ch['name'], ch['topic'], '{}{}'.format(CHANNEL_URL, ch['id']), count])
        groups.extend(channels)

        chat = cls.bot.get_chat(ctx.msg)
        gcount = len(groups)
        if ctx.mode in (Mode.TEXT, Mode.TEXT_HTMLZIP):
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
            cls.bot.send_html(chat, html, cls.name, ctx.msg.text, ctx.mode)

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

        channels = []
        for ch in cls.db.execute('SELECT * FROM channels WHERE status=?', (Status.PUBLIC,)):
            for c in cls.get_cchats(ch['id']):
                if sender in c.get_contacts():
                    channels.append(
                        (ch['name'], '{}{}'.format(CHANNEL_URL, ch['id'])))
                    break
        groups.extend(channels)
        text = ''
        for g in groups:
            text += _('{0}:\nID: {1}\n\n').format(*g)
        if not text:
            text = _('Empty list')
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

    @classmethod
    def channel_cmd(cls, ctx):
        if cls.db.execute('SELECT * FROM channels WHERE name=?', (ctx.text,)).fetchone():
            cls.bot.get_chat(ctx.msg).send_text(
                _('There is already a channel with that name'))
            return
        sender = ctx.msg.get_sender_contact()
        g = cls.bot.create_group(ctx.text, [sender])
        cls.db.execute('INSERT INTO channels VALUES (?,?,?,?,?,?)',
                       (None, cls.generate_pid(), ctx.text, '', Status.PUBLIC, g.id))
        g.send_text(_('Channel created'))


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
        self.execute('''CREATE TABLE IF NOT EXISTS mg_images
                        (mgroup INTEGER PRIMARY KEY REFERENCES mgroups(id),
                         image BLOB NOT NULL,
                         extension TEXT NOT NULL)''')
        self.execute('''CREATE TABLE IF NOT EXISTS mchats
                        (id INTEGER PRIMARY KEY,
                         mgroup INTEGER NOT NULL REFERENCES mgroups(id))''')
        self.execute('''CREATE TABLE IF NOT EXISTS nicks
                        (addr TEXT PRIMARY KEY,
                         nick TEXT NOT NULL)''')
        self.execute('''CREATE TABLE IF NOT EXISTS channels
                        (id INTEGER PRIMARY KEY,
                         pid TEXT NOT NULL,
                         name TEXT NOT NULL,
                         topic TEXT,
                         status INTEGER NOT NULL,
                         admin INTEGER NOT NULL)''')
        self.execute('''CREATE TABLE IF NOT EXISTS channel_images
                        (channel INTEGER PRIMARY KEY REFERENCES channels(id),
                         image BLOB NOT NULL,
                         extension TEXT NOT NULL)''')
        self.execute('''CREATE TABLE IF NOT EXISTS cchats
                        (id INTEGER PRIMARY KEY,
                         channel INTEGER NOT NULL REFERENCES channels(id))''')

    def execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def close(self):
        self.db.close()
