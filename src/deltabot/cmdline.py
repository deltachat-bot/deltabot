# -*- coding: utf-8 -*-

import os
import sys
import copy

import logging.handlers
import click

import deltachat
from .plugins import get_global_plugin_manager
from . import deltabot_hookimpl
from .bot import DeltaBot


@click.command(cls=click.Group, context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--basedir", type=click.Path(),
              default=click.get_app_dir("deltabot"),
              envvar="DELTABOT_BASEDIR",
              help="directory where simplebot state is stored")
@click.option("--stdout-loglevel", type=str,
              default="INFO",
              envvar="DELTABOT_STDOUT_LOGLEVEL",
              help="logging level for stdout logging")
@click.version_option()
@click.pass_context
def bot_main(ctx, basedir, stdout_loglevel):
    """delta.chat bot management command line interface."""
    basedir = os.path.abspath(os.path.expanduser(basedir))
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    db_path = os.path.join(basedir, "account.db")
    account = deltachat.Account(db_path, "deltabot/{}".format(sys.platform))
    loglevel = getattr(logging, stdout_loglevel.upper())
    logger = make_logger(basedir, loglevel)
    ctx.bot = DeltaBot(account, logger, plugin_manager=ctx.obj)


@click.command()
@click.argument("emailaddr", type=str, required=True)
@click.argument("password", type=str, required=True)
@click.pass_context
def init(ctx, emailaddr, password):
    """initialize account with emailadr and password.

    This will set and verify smtp/imap connectivity using the provided credentials.
    """
    if "@" not in emailaddr:
        fail(ctx, "invalid email address: {}".format(emailaddr))
    success = ctx.parent.bot.perform_configure_address(emailaddr, password)
    if not success:
        fail(ctx, "failed to configure with: {}".format(emailaddr))


@click.command()
@click.pass_context
def info(ctx):
    """show information about configured account. """
    bot = ctx.parent.bot
    if not bot.is_configured():
        fail(ctx, "account not configured, use 'deltabot init'")

    for key, val in bot.account.get_info().items():
        print("{:30s}: {}".format(key, val))


@click.command()
@click.pass_context
def list_plugins(ctx):
    """list deltabot plugins. """
    bot = ctx.parent.bot
    for name, plugin in bot.plugins.items():
        print("{:25s}: {}".format(name, plugin))


@click.command()
@click.option("--locale",
              default='en',
              envvar="DELTABOT_LOCALE",
              help="locale for deltabot")
@click.pass_context
def serve(ctx, locale):
    """serve and react to incoming messages"""
    bot = ctx.parent.bot
    bot.locale = locale

    if not bot.is_configured():
        fail(ctx, "account not configured: {}".format(bot.account.db_path))

    bot.start()
    bot.account.wait_shutdown()


def fail(ctx, msg):
    click.secho(msg, fg="red")
    ctx.exit(1)


def make_logger(logdir, stdout_loglevel):
    logger = logging.Logger('deltabot')
    logger.parent = None
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    chandler = logging.StreamHandler()
    chandler.setLevel(stdout_loglevel)
    chandler.setFormatter(formatter)
    logger.addHandler(chandler)

    log_path = os.path.join(logdir, "deltabot.log")
    fhandler = logging.handlers.RotatingFileHandler(
        log_path, backupCount=5, maxBytes=2000000)
    fhandler.setLevel(logging.DEBUG)
    fhandler.setFormatter(formatter)
    logger.addHandler(fhandler)

    return logger


class CmdlinePlugin:
    @deltabot_hookimpl
    def deltabot_init_cmdline(self, plugin_manager, bot_main):
        bot_main.add_command(init)
        bot_main.add_command(info)
        bot_main.add_command(list_plugins)
        bot_main.add_command(serve)


def main():
    pm = get_global_plugin_manager()
    click_group = _get_click_group(pm)
    # pass plugin manager as obj context attribute
    return click_group(obj=pm)


def _get_click_group(pm):
    pm.register(CmdlinePlugin(), "cmdline_plugin")
    pm.check_pending()
    click_group = copy.deepcopy(bot_main)
    pm.hook.deltabot_init_cmdline(bot_main=click_group, plugin_manager=pm)
    return click_group
