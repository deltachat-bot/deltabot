# -*- coding: utf-8 -*-
import string
import random

from jinja2 import Environment, PackageLoader, select_autoescape
from simplebot import Plugin
import deltachat as dc

class GroupMaster(Plugin):

    name = 'GroupMaster'
    description = 'Provides the !group command.'
    long_description = 'Ex. !group !list.'
    version = '0.2.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!group'

    PUBLIC_GROUP = '[pub]'
    MAX_TOPIC_SIZE = 250
    HELP = '\n\n'.join(['!group !list will show the list of public groups and their ID.',
                        '!group !id send this command in a group to see its ID.',
                        '!group !join <ID> will join you to the public group with the given ID.',
                        '!group !leave <ID> will remove you from the group with the given ID.',
                        '!group !public/!private use this commands in a group to make it public or private.',
                        '!group !topic [new topic] replace the current topic or show the current topic if no new topic was provided (topics must be < {} characters).'.format(MAX_TOPIC_SIZE),
                        '!group !add <ID> <addrs> will add a comma-separated list of addresses to the group with the given ID.',
                        '!group !remove <ID> <addr> will remove the member with the given address from the group with the give ID.',
                        '!group !msg <ID> <msg> will send the given message to the group with the given ID.'])
    LISTCMD_BANNER = 'Groups ({}):\n\n'
    UNKNOW_GROUP = 'unknow group ID: {}'
    REMOVED_FROM_GROUP = 'removed from {} [ID:{}]'
    REMOVED_FROM_GROUP_BY = 'removed from {} [ID:{}] by {}'
    ADDED_TO_GROUP = 'added to {} [ID:{}]\n\nTopic:\n{}'
    ADDED_TO_GROUP_BY = 'added to {} [ID:{}] by {}\n\nTopic:\n{}'
    GROUP_STATUS_PUBLIC = 'Group status: Public'
    GROUP_STATUS_PRIVATE = 'Group status: Private'
    TOPIC = 'Topic:\n{}'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        # if ctx.locale == 'es':
        #     cls.description = 'Provee el comando !group, utilice !group !help para más información. Ej. !group !list.'
        #     cls.LISTCMD_BANNER = 'Grupos ({}):\n\n'
        #     cls.UNKNOW_GROUP = 'Grupo desconocido, ID: {}'
        #     cls.REMOVED_FROM_GROUP = 'Fuiste eliminado de {} [ID:{}]'
        #     cls.REMOVED_FROM_GROUP_BY = 'Fuiste eliminado de {} [ID:{}] por {}'
        #     cls.ADDED_TO_GROUP = 'Fuiste añadido a {} [ID:{}]\n\nTema:\n'
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
        chat = cls.ctx.acc.create_chat_by_message(msg)
        req = arg
        for cmd,action in [('!id', cls.id_cmd), ('!list', cls.list_cmd), ('!join', cls.join_cmd),
                           ('!leave', cls.leave_cmd), ('!public', cls.public_cmd), ('!private', cls.private_cmd),
                           ('!topic', cls.topic_cmd), ('!add', cls.add_cmd), ('!remove', cls.remove_cmd),
                           ('!msg', cls.msg_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                text = action(msg, arg)
                break
        else:
            text = cls.name+':\n\n'+cls.HELP
        if text:
            chat.send_text(text)
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
        if msg.chat.get_type() not in (dc.const.DC_CHAT_TYPE_GROUP,
                                       dc.const.DC_CHAT_TYPE_VERIFIED_GROUP):
            return 'Not a group.' # cls.NOT_A_GROUP
        _, _, pub = cls.parse_group_name(msg.chat.get_name())
        if pub:
            gid = msg.chat.id
        else:
            # TODO: load from db if exist, generate otherwise
            gid = ''.join(random.choice(string.ascii_uppercase + string.ascii_lowercase + string.digits)
                          for _ in range(10))
            gid = 'http://delta.chat/join/{}-{}'.format(gid, msg.chat.id)
        return 'ID: {}'.format(gid)

    @classmethod
    def public_cmd(cls, msg, _):
        name = msg.chat.get_name()
        if not name.endswith(cls.PUBLIC_GROUP):
            msg.chat.set_name('{} {}'.format(name, cls.PUBLIC_GROUP))
        return cls.GROUP_STATUS_PUBLIC

    @classmethod
    def private_cmd(cls, msg, _):
        name = msg.chat.get_name()
        if name.endswith(cls.PUBLIC_GROUP):
            msg.chat.set_name(name.strip(cls.PUBLIC_GROUP))
        return cls.GROUP_STATUS_PRIVATE

    @classmethod
    def topic_cmd(cls, msg, new_topic):
        name, topic, pub = cls.parse_group_name(msg.chat.get_name())
        if new_topic:
            if len(new_topic) > 250:
                new_topic = new_topic[:250]+'...'
            msg.chat.set_name('{}: {} {}'.format(name, new_topic, pub))
            topic = new_topic
        return cls.TOPIC.format(topic)

    @classmethod
    def join_cmd(cls, msg, arg):
        group_id = arg
        try:
            group_id = int(group_id)
            for g in cls.get_groups():
                if g.id == group_id:
                    g.add_contact(msg.get_sender_contact())
                    name, topic, _ = cls.parse_group_name(g.get_name())
                    return cls.ADDED_TO_GROUP.format(name, g.id, topic)
        except ValueError:
            pass
        return cls.UNKNOW_GROUP.format(group_id)

    @classmethod
    def leave_cmd(cls, msg, arg):
        group_id = arg
        try:
            group_id = int(group_id)
            for g in cls.get_groups(public_only=False):
                if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                    g.remove_contact(msg.get_sender_contact())
                    name, _, _ = cls.parse_group_name(g.get_name())
                    return cls.REMOVED_FROM_GROUP.format(name, g.id)
        except ValueError:
            pass
        return cls.UNKNOW_GROUP.format(group_id)

    @classmethod
    def add_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i])
            addrs = arg[i:].strip().split(',')
            if i < 0 or not addrs:
                raise ValueError
        except ValueError:
            return cls.name+':\n\n'+cls.HELP
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                name, topic, _ = cls.parse_group_name(g.get_name())
                author = msg.get_sender_contact().addr
                for addr in addrs:
                    c = cls.ctx.acc.create_contact(addr.strip())
                    g.add_contact(c)
                    chat = cls.ctx.acc.create_chat_by_contact(c)
                    chat.send_text(cls.ADDED_TO_GROUP_BY.format(name, g.id, author, topic))
                return ''

    @classmethod
    def remove_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i])
            addr = arg[i:].strip()
            if i < 0 or not addrs:
                raise ValueError
        except ValueError:
            return cls.name+':\n\n'+cls.HELP
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                c = [c for c in cls.ctx.acc.get_contacts(addr) if c.addr == addr][0]  # TODO: error if addr not in group
                g.remove_contact(c)
                chat = cls.ctx.acc.create_chat_by_contact(c)
                chat.send_text(cls.REMOVED_FROM_GROUP_BY.format(name, g.id, author))
                return ''

    @classmethod
    def msg_cmd(cls, msg, arg):
        i = arg.find(' ')
        try:
            group_id = int(arg[:i])
            text = arg[i:].strip()
            if i < 0 or not msg:
                raise ValueError
        except ValueError:
            return cls.name+':\n\n'+cls.HELP
        sender = msg.get_sender_contact()
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and sender in g.get_contacts():
                g.send_text('{}:\n{}'.format(sender.addr, text))
                return ''

    @classmethod
    def list_cmd(cls, msg, arg):
        groups = cls.get_groups()
        groups.sort(key=lambda g: g.get_name())
        text = cls.LISTCMD_BANNER.format(len(groups))
        for g in groups:
            name, _, _ = cls.parse_group_name(g.get_name())
            text += '{} [ID:{}]:\n* {} 👤\n'.format(name, g.id, len(g.get_contacts()))
        return text
