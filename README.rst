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


Official Plugins
----------------

- **Admin:** Administration tools for bot operators.
- **Avatar:** Generates `cats <https://www.peppercarrot.com/extras/html/2016_cat-generator>`_ and `birds <https://www.peppercarrot.com/extras/html/2019_bird-generator>`_ avatars.
- **Echo:** Simple plugin to echo back text.
- **FB Messenger:** Facebook Messenger bridge.
- **DeltaFriends:** Provides a directory for users to share their address and biography.
- **GroupMaster:** Extends the capabilities of Delta Chat groups, adding "mega groups", "channels", and allowing to have public groups, invite friends to join a group with a private link, set group topic, etc.
- **Help:** Provides a help command.
- **Mastodon Bridge:** A bridge between Delta Chat and Mastodon network.
- **RSS:** Subscribe to RSS and Atom links.
- **Shortcuts:** Allows to create custom shortcuts for commands.
- **Tic Tac Toe:** The simple Tic Tac Toe game to play with friends.
- **Translator:** Allows to translate text. Example: /tr en es hello world.
- **WebGrabber:** Access the web using Delta Chat.
- **Wikiquote:** Get quotes from Wikiquote on Delta Chat.
- **XKCD:** See xkcd.com comics in Delta Chat.


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


Contributors
============

- Asiel Díaz Benítez (@adbenitez)
- Luis Antonio Correa Leyva (@correaleyval)


License
=======

This project is **free software**, licensed under the **GPL3** License - see the `LICENSE <https://github.com/adbenitez/simplebot/blob/master/LICENSE>`_ file for more details.


.. _Delta Chat: https://delta.chat
