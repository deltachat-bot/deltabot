
import os
import logging.handlers
from deltabot import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_get_logger(args):
    loglevel = getattr(logging, args.stdout_loglevel.upper())
    return make_logger(args.basedir, loglevel)


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
