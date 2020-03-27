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


Implementing a calculator bot
-----------------------------

Here is a complete "calculator" chat bot for performing additions::

    # contents of mycalc.py
    from deltabot import deltabot_hookimpl

    @deltabot_hookimpl
    def deltabot_configure(bot, trans):
        bot.add_command(
            name="/mycalc",
            version="1.0",
            description=trans('caculcates result of arithmetic integer expression'),
            long_description=trans(
                'send "/calc 23+20" to the bot to get the result "43" back'),
            func=process_command_mycalc
        )


    def process_command_mycalc(command):
        assert command.arg0 == "/mycalc"
        text = command.payload

        # don't directly use eval() as it could execute arbitrary code
        parts = text.split("+-*/")
        try:
            for part in parts:
                int(part)
        except ValueError:
            reply = "ExpressionError: {!r}".format(text)
        else:
            reply = "result of {!r}: {}".format(text, eval(text))

        command.message.chat.send_text(reply)

Register the new "echo bot"::

    $ deltabot add-plugin mycalc.py

Now start serving the chat bot::

    $ deltabot serve

and text a `/calc 23+20-1` message, and see the result message arriving back.


note for users
--------------

Deltabot uses `Autocrypt <https://autocrypt.org/>`_ end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.


Plugins
-------

See: https://github.com/SimpleBot-Inc/simplebot_plugins


.. _Delta Chat: https://delta.chat
