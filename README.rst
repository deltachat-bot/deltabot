.. image:: artwork/simplebot-banner.png
  :align: center
  :alt: SimpleBot Logo


SimpleBot
=========

A simple "deltabot" that depends on plugins to add functionality.
It works as part of a group or in 1:1 chats in `Delta Chat`_
applications. SimpleBot supports `Autocrypt <https://autocrypt.org/>`_ end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it. See also: https://github.com/Simon-Laux/ZHV/


Install
-------

To install it run the following command (preferably in a ``virtualenv``):

.. code-block:: bash

   $ pip3 install simplebot

Then install `some plugins <https://pypi.org/search/?q=simplebot&o=&c=Environment+%3A%3A+Plugins>`_


Starting the bot
----------------

First you need to provide an emailaddress and a password
to allow the bot to receive and send messages for that
address:

.. code-block:: bash

   $ simplebot init "email@example.org" "password123"

This command will try to contact the imap/smtp servers
for ``example.org`` and logging in with the given e-mail
address and password.  Once this successfully completes,
initialization is done and tested.

You can then let the bot listen continously:

.. code-block:: bash

   $ simplebot serve

It will listen for incoming messages and handle them with installed plugins.

Install `Delta Chat`_ and add your bot's email address as a contact and
start chatting with it! You can also add the bot as a member to a group chat.


Plugins
-------

See: https://github.com/SimpleBot-Inc/simplebot_plugins


License
=======

This project is **free software**, licensed under the **GPL3** License - see the `LICENSE <https://github.com/SimpleBot-Inc/simplebot/blob/master/LICENSE>`_ file for more details.


.. _Delta Chat: https://delta.chat
