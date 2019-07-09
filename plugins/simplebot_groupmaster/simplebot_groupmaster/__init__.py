# -*- coding: utf-8 -*-
import os
import string
import random

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin
import deltachat as dc

class GroupMaster(Plugin):

    name = 'GroupMaster'
    description = 'Provides the !group command.'
    MAX_TOPIC_SIZE = 250
    long_description = '<br><br>'.join(['!group !list will show the list of public groups and their ID.',
                                        '!group !id send this command in a group to see its ID.',
                                        '!group !join <ID> will join you to the public group with the given ID.',
                                        '!group !leave <ID> will remove you from the group with the given ID.',
                                        '!group !public/!private use this commands in a group to make it public or private.',
                                        '!group !topic [new topic] replace the current topic or show the current topic if no new topic was provided (topics must be < {} characters).'.format(MAX_TOPIC_SIZE),
                                        '!group !add <ID> <addrs> will add a comma-separated list of addresses to the group with the given ID.',
                                        '!group !remove <ID> <addr> will remove the member with the given address from the group with the give ID.',
                                        '!group !msg <ID> <msg> will send the given message to the group with the given ID.'])
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!group!list'

    PUBLIC_GROUP = '[pub]'
    LISTCMD_BANNER = 'Groups ({}):\n\n'
    UNKNOW_GROUP = 'unknow group ID: {}'
    REMOVED_FROM_GROUP = 'removed from {} [ID:{}]'
    REMOVED_FROM_GROUP_BY = 'removed from {} [ID:{}] by {}'
    ADDED_TO_GROUP = 'added to {} [ID:{}]\n\nTopic:\n{}'
    ADDED_TO_GROUP_BY = 'added to {} [ID:{}] by {}\n\nTopic:\n{}'
    GROUP_STATUS_PUBLIC = 'Group status: Public'
    GROUP_STATUS_PRIVATE = 'Group status: Private'
    DELTA_URL = 'http://delta.chat/group/'
    LIST_BTN = 'Groups List'
    TOPIC = 'Topic:\n{}'
    JOIN_BTN = 'Join'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            #autoescape=select_autoescape(['html', 'xml'])
        )
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando !group, utilice !group !help para más información. Ej. !group !list.'
        #     cls.LISTCMD_BANNER = 'Grupos ({}):\n\n'
        #     cls.UNKNOW_GROUP = 'Grupo desconocido, ID: {}'
        #     cls.REMOVED_FROM_GROUP = 'Fuiste eliminado de {} [ID:{}]'
        #     cls.REMOVED_FROM_GROUP_BY = 'Fuiste eliminado de {} [ID:{}] por {}'
        #     cls.ADDED_TO_GROUP = 'Fuiste añadido a {} [ID:{}]\n\nTema:\n{}'
        #     cls.ADDED_TO_GROUP_BY = 'Fuiste añadido a {} [ID:{}] por {}\n\nTema:\n'
        #     cls.HELP = '\n\n'.join(['!group !list muestra la lista de grupos públicos y sus ID.',
        #                             '!group !id envia este comando en un grupo para obtener su ID.',
        #                             '!group !join te permite unirte al grupo público con el ID dado.',
        #                             '!group !leave <ID> usa este comando para abandonar el grupo con el ID dado.',
        #                             '!group !public/!private usa estos comandos en un grupo para hacerlo público o privado.',
        #                             '!group !topic [nuevo tema] sustituye el tema actual o muestra el tema actual si no es dado uno nuevo (tamaño máximo del tema: {} caracteres).'.format(cls.MAX_TOPIC_SIZE),
        #                             '!group !add <ID> <correos> permite agregar una lista separada por comas de direcciones de correo al grupo con el  ID dado.',
        #                             '!group !remove <ID> <correo> permite eliminar un miembro del grupo con el ID dado.',
        #                             '!group !msg <ID> <msg> permite enviar un mensaje al grupo con el ID dado.'])
        #     cls.GROUP_STATUS_PUBLIC = 'Estado del grupo: Público'
        #     cls.GROUP_STATUS_PRIVATE = 'Estado del grupo: Privado'
        #     cls.TOPIC = 'Tema:\n{}'

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
    def parse_group_name(cls, group_name):
        title = group_name.split(':')
        name = title[0].strip()
        topic = ''
        pub = ''
        if len(title) > 1:
            topic = ':'.join(title[1:])
            if topic.endswith(cls.PUBLIC_GROUP):
                topic = topic.strip(cls.PUBLIC_GROUP).strip()
                pub = cls.PUBLIC_GROUP
        else:
            if name.endswith(cls.PUBLIC_GROUP):
                name = name.strip(cls.PUBLIC_GROUP).strip()
                pub = cls.PUBLIC_GROUP
        return (name, topic, pub)

    @classmethod
    def get_groups(cls, public_only=True):
        me = cls.ctx.acc.get_self_contact()
        groups = []
        for chat in cls.ctx.acc.get_chats():
            if chat.get_type() in (dc.const.DC_CHAT_TYPE_GROUP,
                                   dc.const.DC_CHAT_TYPE_VERIFIED_GROUP):
                if me not in chat.get_contacts():
                    chat.delete()
                else:
                    if public_only and not chat.get_name().endswith(cls.PUBLIC_GROUP):
                        continue
                    groups.append(chat)
        return groups

    @classmethod
    def id_cmd(cls, msg, _):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        if msg.chat.get_type() not in (dc.const.DC_CHAT_TYPE_GROUP,
                                       dc.const.DC_CHAT_TYPE_VERIFIED_GROUP):
            text = 'Not a group.' # cls.NOT_A_GROUP
        else:
            _, _, pub = cls.parse_group_name(msg.chat.get_name())
            if pub:
                gid = '{}{}'.format(cls.DELTA_URL, msg.chat.id)
            else:
                # TODO: load from db if exist, generate otherwise
                gid = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                              for _ in range(10))
                gid = '{}{}-{}'.format(cls.DELTA_URL, gid, msg.chat.id)
                text = 'ID: {}'.format(gid)
        chat.send_text(text)

    @classmethod
    def public_cmd(cls, msg, _):
        name = msg.chat.get_name()
        if not name.endswith(cls.PUBLIC_GROUP):
            msg.chat.set_name('{} {}'.format(name, cls.PUBLIC_GROUP))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(cls.GROUP_STATUS_PUBLIC)

    @classmethod
    def private_cmd(cls, msg, _):
        name = msg.chat.get_name()
        if name.endswith(cls.PUBLIC_GROUP):
            msg.chat.set_name(name.strip(cls.PUBLIC_GROUP))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(cls.GROUP_STATUS_PRIVATE)

    @classmethod
    def topic_cmd(cls, msg, new_topic):
        name, topic, pub = cls.parse_group_name(msg.chat.get_name())
        if new_topic:
            if len(new_topic) > 250:
                new_topic = new_topic[:250]+'...'
            msg.chat.set_name('{}: {} {}'.format(name, new_topic, pub))
            topic = new_topic
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text(cls.TOPIC.format(topic))

    @classmethod
    def join_cmd(cls, msg, arg):
        group_id = arg
        chat = cls.ctx.acc.create_chat_by_message(msg)
        try:
            group_id = int(group_id.strip(cls.DELTA_URL))
            for g in cls.get_groups():
                if g.id == group_id:
                    g.add_contact(msg.get_sender_contact())
                    name, topic, _ = cls.parse_group_name(g.get_name())
                    chat.send_text(cls.ADDED_TO_GROUP.format(name, g.id, topic))
                    return
        except ValueError:
            pass
        chat.send_text(cls.UNKNOW_GROUP.format(group_id))

    @classmethod
    def leave_cmd(cls, msg, arg):
        group_id = arg
        chat = cls.ctx.acc.create_chat_by_message(msg)
        try:
            group_id = int(group_id.strip(cls.DELTA_URL))
            for g in cls.get_groups(public_only=False):
                if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                    g.remove_contact(msg.get_sender_contact())
                    name, _, _ = cls.parse_group_name(g.get_name())
                    chat.send_text(cls.REMOVED_FROM_GROUP.format(name, g.id))
                    return
        except ValueError:
            pass
        chat.send_text(cls.UNKNOW_GROUP.format(group_id))

    @classmethod
    def add_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i].strip(cls.DELTA_URL))
            addrs = arg[i:].strip().split(',')
            if i < 0 or not addrs:
                raise ValueError
        except ValueError:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(cls.name+':\n\n'+cls.long_description)
            return
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                name, topic, _ = cls.parse_group_name(g.get_name())
                author = msg.get_sender_contact().addr
                for addr in addrs:
                    c = cls.ctx.acc.create_contact(addr.strip())
                    g.add_contact(c)
                    chat = cls.ctx.acc.create_chat_by_contact(c)
                    chat.send_text(cls.ADDED_TO_GROUP_BY.format(name, g.id, author, topic))
                break

    @classmethod
    def remove_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i].strip(cls.DELTA_URL))
            addr = arg[i:].strip()
            if i < 0 or not addrs:
                raise ValueError
        except ValueError:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(cls.name+':\n\n'+cls.long_description)
            return
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                c = [c for c in cls.ctx.acc.get_contacts(addr) if c.addr == addr][0]  # TODO: error if addr not in group
                g.remove_contact(c)
                chat = cls.ctx.acc.create_chat_by_contact(c)
                chat.send_text(cls.REMOVED_FROM_GROUP_BY.format(name, g.id, author))
                break

    @classmethod
    def msg_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i].strip(cls.DELTA_URL))
            text = arg[i:].strip()
            if i < 0 or not msg:
                raise ValueError
        except ValueError:
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(cls.name+':\n\n'+cls.long_description)
            return
        sender = msg.get_sender_contact()
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and sender in g.get_contacts():
                g.send_text('{}:\n{}'.format(sender.addr, text))
                break

    @classmethod
    def list_cmd(cls, msg, arg):
        groups = cls.get_groups()
        groups.sort(key=lambda g: g.get_name())
        gs = []
        for g in groups:
            name, topic, _ = cls.parse_group_name(g.get_name())
            gs.append(name, topic, '{}{}'.format(cls.DELTA_URL,g.id), len(g.get_contacts()))
        template = cls.env.get_template('list.html')
        with open(cls.TEMP_FILE, 'w') as fd:
            fd.write(template.render(plugin=cls, bot_addr=cls.ctx.acc.get_self_contact().addr, groups=gs))
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_file(cls.TEMP_FILE, mime_type='text/html')
        # text = cls.LISTCMD_BANNER.format(len(groups))
        # for g in groups:
        #     name, _, _ = cls.parse_group_name(g.get_name())
        #     text += '{} [ID:{}{}]:\n* {} 👤\n'.format(name, cls.DELTA_URL, g.id, len(g.get_contacts()))
        # return text
