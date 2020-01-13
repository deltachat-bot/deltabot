# -*- coding: utf-8 -*-
from . import SimpleBot
import click


@click.command(cls=click.Group, context_settings=dict(help_option_names=["-h", "--help"]))
@click.option("--basedir", type=click.Path(),
              default=click.get_app_dir("simplebot"),
              envvar="SIMPLEBOT_BASEDIR",
              help="directory where simplebot state is stored")
@click.version_option()
@click.pass_context
def bot_main(ctx, basedir):
    """delta.chat bot management command line interface."""
    ctx.bot = SimpleBot(basedir)


@click.command()
@click.argument("emailaddr", type=str, required=True)
@click.argument("password", type=str, required=True)
@click.pass_context
def init(ctx, emailaddr, password):
    """initialize account with emailadr and password.

    This will verify smtp/imap connectivity.
    """
    if "@" not in emailaddr:
        fail(ctx, "invalid email address: {}".format(emailaddr))
    ctx.parent.bot.configure(emailaddr, password)


@click.command()
@click.pass_context
def info(ctx):
    """show information about configured account. """
    bot = ctx.parent.bot
    if not bot.is_configured():
        fail(ctx, "account not configured, use 'simplebot init'")

    info = bot.account.get_infostring()
    print(info)


@click.command()
@click.option("--locale",
              default='en',
              envvar="SIMPLEBOT_LOCALE",
              help="locale for simplebot")
@click.pass_context
def serve(ctx, locale):
    """serve and react to incoming messages"""
    bot = ctx.parent.bot
    bot.locale = locale

    if not bot.is_configured():
        fail(ctx, "account not configured: {}".format(bot.account.db_path))

    bot.start()


def fail(ctx, msg):
    click.secho(msg, fg="red")
    ctx.exit(1)


bot_main.add_command(init)
bot_main.add_command(info)
bot_main.add_command(serve)


if __name__ == "__main__":
    bot_main()
