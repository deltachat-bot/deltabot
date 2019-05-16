# -*- coding: utf-8 -*-
from simplebot import Plugin

import deltachat


class GroupMaster(Plugin):

    name = 'GroupMaster'
    description = 'Provides the !group command, use !group !help for more info. Ex. !group !list.'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    PUBLIC_GROUP = '[pub]'
    HELP = '!group !list will show the list of public groups and their ID.\n\n!group !id send this command in a group to see its ID.\n\n!group !join <ID> will join you to the public group with the given ID.\n\n!group !leave ID will remove you from the group with the given ID.\n\nTo make a group public add this bot to the group and append the keyword "[pub]" to the name of the group (ex. YourGroupName [pub]), to make the group private again, remove the keyword "[pub]" from its name or remove the bot from the group.'
    LISTCMD_BANNER = 'Groups (%s):\n\n'
    UNKNOW_GROUP = 'unknow group ID: %s'
    REMOVED_FROM_GROUP = 'removed from %s [ID:%s]'
    ADDED_TO_GROUP = 'added to %s [ID:%s]'

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        if ctx.locale == 'es':
            cls.description = 'Provee el comando !group, utilice !group !help para más información. Ej. !group !list.'
            cls.LISTCMD_BANNER = 'Grupos (%s):\n\n'
            cls.UNKNOW_GROUP = 'Grupo desconocido, ID: %s'
            cls.REMOVED_FROM_GROUP = 'Fuiste eliminado de %s [ID:%s]'
            cls.ADDED_TO_GROUP = 'Fuiste añadido a %s [ID:%s]'
            cls.HELP = '!group !list muestra la lista de grupos públicos y sus ID.\n\n!group !id envia este comando en un grupo para obtener su ID.\n\n!group !join <ID> te permite unirte al grupo público con el ID dado.\n\n!group !leave ID usa este comando para abandonar el grupo con el ID dado.\n\nPara hacer un grupo público, añade este bot al grupo y agrega la palabra "[pub]" al final del nombre del grupo (ej. NombreDelGrupo [pub]), para hacer el grupo privado otra vez, elimina la palabra "[pub]" del nombre del grupo o quita este bot del grupo.'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!group', msg.text)
        if arg is None:
            return False
        chat = cls.ctx.acc.create_chat_by_message(msg)
        req = arg
        for cmd,action in [('!id', cls.id_cmd), ('!list', cls.list_cmd), ('!join', cls.join_cmd), ('!leave', cls.leave_cmd)]:
            arg = cls.get_args(cmd, req)
            if arg is not None:
                text = action(msg, arg)
                break
        else:
            text = cls.name+':\n\n'+cls.HELP
        chat.send_text(text)
        return True

    @classmethod
    def get_groups(cls, public_only=True):
        me = cls.ctx.acc.get_self_contact()
        groups = []
        for chat in cls.ctx.acc.get_chats():
            if deltachat.capi.lib.dc_chat_get_type(chat._dc_chat) == 120:
                if me not in chat.get_contacts():
                    chat.delete()
                else:
                    if public_only and not chat.get_name().endswith(cls.PUBLIC_GROUP):
                        continue
                    groups.append(chat)
        return groups

    @classmethod
    def id_cmd(cls, msg, arg):
        return 'ID: %s' % (msg.chat.id,)

    @classmethod
    def join_cmd(cls, msg, arg):
        group_id = int(arg)
        for g in cls.get_groups():
            if g.id == group_id:
                g.add_contact(msg.get_sender_contact())
                return cls.ADDED_TO_GROUP % (g.get_name(), g.id)
        return cls.UNKNOW_GROUP % group_id

    @classmethod
    def leave_cmd(cls, msg, arg):
        group_id = int(arg)
        for g in cls.get_groups(public_only=False):
            if g.id == group_id and msg.get_sender_contact() in g.get_contacts():
                deltachat.capi.lib.dc_remove_contact_from_chat(g._dc_context, g.id, msg.get_sender_contact().id)
                return cls.REMOVED_FROM_GROUP % (g.get_name(), g.id)
        return cls.UNKNOW_GROUP % (group_id,)
        

    @classmethod
    def list_cmd(cls, msg, arg):
        groups = cls.get_groups()
        groups.sort(key=lambda g: g.get_name())
        text = cls.LISTCMD_BANNER % (len(groups),)
        for g in groups:
            text += '%s [ID:%s]:\n* %s 👤\n' % (g.get_name(), g.id, len(g.get_contacts()))
        return text
