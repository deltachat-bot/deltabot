# -*- coding: utf-8 -*-
import configparser
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


def load_plugins(ctx):
    ctx.plugins = []
    for ep in pkg_resources.iter_entry_points('simplebot.plugins'):
        try:
            ctx.plugins.append(ep.load())
        except Exception as ex:
            ctx.logger.exception(ex)


def activate_plugins(ctx):
    for plugin in ctx.plugins:
        try:
            plugin.activate(ctx)
        except Exception as ex:
            ctx.logger.exception(ex)
            ctx.plugins.remove(plugin)


def deactivate_plugins(ctx):
    for plugin in ctx.plugins:
        try:
            plugin.deactivate(ctx)
        except Exception as ex:
            ctx.logger.exception(ex)

                
@click.command(cls=click.Group, context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--basedir", type=click.Path(),
              default=click.get_app_dir("simplebot"),
              envvar="SIMPLEBOT_BASEDIR",
              help="directory where simplebot state is stored")
@click.version_option()
@click.pass_context
def bot_main(ctx, basedir):
    """delta.chat bot management command line interface."""
    basedir = os.path.abspath(os.path.expanduser(basedir))
    if not os.path.exists(basedir):
        os.makedirs(basedir)
    ctx.basedir = basedir


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
    context.basedir = ctx.parent.basedir
    context.locale = locale
    context.logger = get_logger()
    
    acc = get_account(ctx.parent.basedir)
    if not acc.is_configured():
        fail(ctx, "account not configured: {}".format(acc.db_path))

    CFG_PATH = os.path.join(context.basedir, 'simplebot.cfg')
    cfg = configparser.ConfigParser(allow_no_value=True)
    if os.path.exists(CFG_PATH):
        cfg.read(CFG_PATH)
        botcfg = cfg['simplebot']
    else:
        cfg.add_section('simplebot')
        botcfg = cfg['simplebot']
        botcfg['e2ee_enabled'] = '1'
        botcfg['mdns_enabled'] = '0'
        botcfg['sentbox_watch'] = '0'
        botcfg['mvbox_watch'] = '0'
        botcfg['mvbox_move'] = '1'
        botcfg['displayname'] = 'SimpleBot🤖'
        with open(CFG_PATH, 'w') as fd:
            cfg.write(fd)
    acc.set_config("save_mime_headers", "1")
    acc.set_config('mdns_enabled', botcfg['mdns_enabled'])
    acc.set_config('sentbox_watch', botcfg['sentbox_watch'])
    acc.set_config('mvbox_watch', botcfg['mvbox_watch'])
    acc.set_config('mvbox_move', botcfg['mvbox_move'])
    acc.set_config('displayname', botcfg['displayname'])
    acc.set_config('e2ee_enabled', botcfg['e2ee_enabled'])

    context.acc = acc
    
    load_plugins(context)
    activate_plugins(context)

    context.acc.start_threads()
    try:
        Runner(context).serve()
    finally:
        deactivate_plugins(context)
        context.acc.stop_threads()


class Runner:
    def __init__(self, ctx):
        self.ctx = ctx

    def process_message(self, msgid):
        msg = self.ctx.acc.get_message_by_id(int(msgid))
        sender_contact = msg.get_sender_contact()
        if sender_contact != self.ctx.acc.get_self_contact():
            self.ctx.logger.debug('Received message from %s' % (sender_contact.addr,))
            for plugin in self.ctx.plugins:
                try:
                    if plugin.process(msg):
                        self.ctx.logger.debug('Message processed by '+plugin.name)
                        break
                except Exception as ex:
                    self.ctx.logger.exception(ex)
        self.ctx.acc.mark_seen_messages([msg])

    def serve(self):
        print("start serve")
        while 1:
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
