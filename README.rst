Deltabot Quickstart: implement and run a chat bot with Python
=============================================================

Deltabot allows to implement and run chat bots for `Delta Chat`_.

Install
-------

To install it run the following command (preferably in a ``virtualenv``):

.. code-block:: bash

   $ pip3 install deltabot


Init and run a bare bot
-----------------------

Configure an e-mail address for your chat bot::

    deltabot init tmp.vd9dd@testrun.org OzrSxdx5hiaD

Now start the bot::

    deltabot serve

Within an Delta Chat app, you may now send a chat `/help` message to
`tmp.vd9dd@testrun.org` and should get a short list of available
commands in the reply.


Implementing an echo bot
------------------------

Here is an "echo" chat bot Python module::

    # contents of echo.py
    from deltabot.hookspec import deltabot_hookimpl

    @deltabot_hookimpl
    def deltabot_configure(bot, trans):
        deltabot_account.add_command(
            name="/echo",
            version="1.0",
            description=trans('Echoes back the given text.'),
            long_description=trans(
                'To use it you can simply send a message starting with '
                'the command /echo. For example:\n/echo hello world'),
            func=process_command_echo
        )


    def process_command_echo(command):
        assert command.arg0 == "/echo"
        text = command.payload
        if not text:
            message = command.message
            f = message.get_mime_headers()['from']
            name = message.get_sender_contact().display_name
            text = 'From: {}\nDisplay Name: {}'.format(f, name)
        command.message.chat.send_text(text)

Register the new "echo bot"::

    deltabot add-plugin echo.py

Now start serving again::

    deltabot serve

and text a `/echo hello123` message, and see the message arriving back.


note for users
--------------

Deltabot uses `Autocrypt <https://autocrypt.org/>`_ end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.


Plugins
-------

See: https://github.com/SimpleBot-Inc/simplebot_plugins


.. _Delta Chat: https://delta.chat
