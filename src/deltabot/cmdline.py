# -*- coding: utf-8 -*-

import os
import sys

import logging.handlers

import deltachat
from .plugins import get_global_plugin_manager
from .bot import DeltaBot
from .parser import get_base_parser


def make_bot(args, plugin_manager, account=None):
    """delta.chat bot management command line interface."""
    basedir = os.path.abspath(os.path.expanduser(args.basedir))
    if not os.path.exists(basedir):
        os.makedirs(basedir)

    if account is None:
        db_path = os.path.join(basedir, "account.db")
        account = deltachat.Account(db_path, "deltabot/{}".format(sys.platform))
    loglevel = getattr(logging, args.stdout_loglevel.upper())
    logger = make_logger(basedir, loglevel)
    return DeltaBot(account, logger, plugin_manager=plugin_manager)


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


def main(argv=None):
    pm = get_global_plugin_manager()
    parser = get_base_parser(plugin_manager=pm)
    args = parser.main_parse_argv(argv or sys.argv)
    bot = make_bot(args, plugin_manager=pm)
    parser.main_run(bot=bot, args=args)
