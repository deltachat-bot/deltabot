from __future__ import print_function
import importlib
import os
import time

import click
import deltachat


@click.command(cls=click.Group, context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--basedir", type=click.Path(),
              default=click.get_app_dir("deltabot"),
              envvar="DELTABOT_BASEDIR",
              help="directory where deltabot state is stored")
@click.version_option()
@click.pass_context
def bot_main(context, basedir):
    """delta.chat bot management command line interface. """
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
        fail(ctx, "account not configured, use 'deltabot init'")

    info = acc.get_infostring()
    print(info)


@click.command()
@click.argument("botname", type=str, required=True)
@click.option("--debug", "-d", default=False, is_flag=True,
              help="add debug information in standard output")
@click.pass_context
def run(ctx, botname, debug=False):
    """run and react to incoming messages"""
    acc = get_account(ctx.parent.basedir)

    if not acc.is_configured():
        fail(ctx, "account not configured: {}".format(acc.db_path))
    acc.set_config("save_mime_headers", "1")
    acc.start_threads()

    runner = get_runner(botname, acc, debug=debug)

    try:
        runner.run()
    finally:
        acc.stop_threads()


def get_runner(botname, acc, debug):
    runner = None
    runner_class = 'Runner'

    py_mod = importlib.import_module('.' + botname, package='deltabot')

    if hasattr(py_mod, runner_class):
        runner = getattr(py_mod, runner_class)(acc, debug)
    return runner


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
bot_main.add_command(run)


if __name__ == "__main__":
    bot_main()
