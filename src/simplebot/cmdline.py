# -*- coding: utf-8 -*-
import logging
import os
import time

import click
import deltachat
import pkg_resources
import simplebot


def get_logger():
    logger = logging.Logger('SimpleBot')
    logger.parent = None
    chandler = logging.StreamHandler()
    chandler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    chandler.setFormatter(formatter)
    logger.addHandler(chandler)
    return logger
    
@click.command(cls=click.Group, context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--basedir", type=click.Path(),
              default=click.get_app_dir("simplebot"),
              envvar="SIMPLEBOT_BASEDIR",
              help="directory where simplebot state is stored")
@click.version_option()
@click.pass_context
def bot_main(context, basedir):
    """delta.chat bot management command line interface."""
    basedir = os.path.abspath(os.path.expanduser(basedir))
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    context.basedir = basedir


@click.command()
@click.argument("emailadr", type=str, required=True)
@click.argument("password", type=str, required=True)
@click.option("--overwrite", default=False, is_flag=True,
              help="overwrite existing configuration and account state")
@click.pass_context
def init(ctx, emailadr, password, overwrite):
    """initialize account with emailadr and password.

    This will verify smtp/imap connectivity.
    """
    if "@" not in emailadr:
        fail(ctx, "invalid email address: {}".format(msg))

    acc = get_account(ctx.parent.basedir, remove=overwrite)
    if acc.is_configured():
        fail(ctx, "account already configured, use --overwrite")

    acc.configure(addr=emailadr, mail_pw=password)
    acc.start_threads()
    wait_configuration_progress(acc, 1000)
    acc.stop_threads()


@click.command()
@click.pass_context
def info(ctx):
    """show information about configured account. """
    acc = get_account(ctx.parent.basedir)
    if not acc.is_configured():
        fail(ctx, "account not configured, use 'simplebot init'")

    info = acc.get_infostring()
    print(info)


@click.command()
@click.option("--locale",
              default='en',
              envvar="SIMPLEBOT_LOCALE",
              help="locale for simplebot")
@click.pass_context
def serve(ctx, locale):
    """serve and react to incoming messages"""
    context = simplebot.Context
    context.locale = locale
    context.logger = get_logger()
    
    acc = get_account(ctx.parent.basedir)
    if not acc.is_configured():
        fail(ctx, "account not configured: {}".format(acc.db_path))
    acc.set_config("save_mime_headers", "1")
    context.acc = acc
    
    plugins = []
    for ep in pkg_resources.iter_entry_points('simplebot.plugins'):
        try:
            plugins.append(ep.load())
        except Exception as ex:
            context.logger.exception(ex)
    context.plugins = plugins
    
    for plugin in context.plugins:
        try:
            plugin.activate(context)
        except Exception as ex:
            context.logger.exception(ex)
            context.plugins.remove(plugin)
            
    context.acc.start_threads()
    try:
        Runner(context).serve()
    finally:
        for plugin in context.plugins:
            try:
                plugin.deactivate(context)
            except Exception as ex:
                context.logger.exception(ex)
        context.acc.stop_threads()


class Runner:
    def __init__(self, ctx):
        self.ctx = ctx

    def process_message(self, msgid):
        msg = self.ctx.acc.get_message_by_id(int(msgid))
        sender_contact = msg.get_sender_contact()
        if sender_contact != self.ctx.acc.get_self_contact():
            self.ctx.logger.debug('Received message from %s: %s' % (sender_contact.addr, msg.text))
            for plugin in self.ctx.plugins:
                try:
                    if plugin.process(msg):
                        self.ctx.logger.debug('Message processed by '+plugin.name)
                        break
                except Exception as ex:
                    self.ctx.logger.exception(ex)
        self.ctx.acc.mark_seen_messages([msg])

    def dump_chats(self):
        print("*" * 80)
        chatlist = self.ctx.acc.get_chats()
        for chat in chatlist:
            print ("chat id={}, name={}".format(chat.id, chat.get_name()))
            for sub in chat.get_contacts():
                print("  member:", sub.addr)
            for msg in chat.get_messages()[-10:]:
                print(u"  msg {}, from {}: {!r}".format(
                      msg.id,
                      msg.get_sender_contact().addr,
                      msg.text))

    def serve(self):
        print("start serve")
        while 1:
            # self.dump_chats()
            # wait for incoming messages
            # DC_EVENT_MSGS_CHANGED for unknown contacts
            # DC_EVENT_INCOMING_MSG for known contacts
            in_events = "DC_EVENT_MSGS_CHANGED|DC_EVENT_INCOMING_MSG"
            ev = self.ctx.acc._evlogger.get_matching(in_events)
            if ev[2] == 0:                
                print (ev)
                continue
            self.process_message(msgid=ev[2])


def wait_configuration_progress(account, target):
    """ wait until configure is completed. """
    while 1:
        evt_name, data1, data2 = \
            account._evlogger.get_matching("DC_EVENT_CONFIGURE_PROGRESS")
        if data1 >= target:
            print("** CONFIG PROGRESS {}".format(target), account)
            return data1


def fail(ctx, msg):
    click.secho(msg, fg="red")
    ctx.exit(1)


def get_account(basedir, remove=False):
    dbpath = os.path.join(basedir, "account.db")
    if remove and os.path.exists(dbpath):
        os.remove(dbpath)
    acc = deltachat.Account(dbpath)
    acc.db_path = dbpath
    return acc


bot_main.add_command(init)
bot_main.add_command(info)
bot_main.add_command(serve)


if __name__ == "__main__":
    bot_main()
