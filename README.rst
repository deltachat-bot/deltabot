.. image:: artwork/simplebot-banner.png
  :align: center
  :alt: SimpleBot Logo


SimpleBot
=========

A simple "deltabot" that depends on plugins to add functionality.
It works as part of a group or in 1:1 chats in https://delta.chat
applications. SimpleBot supports Autocrypt end-to-end encryption
but note that the operator of the bot service can look into
messages that are sent to it.


Official Plugins
----------------

- **Admin:** Administration tools for bot operators.
- **Echo:** Simple plugin to echo back text.
- **FB Messenger:** Facebook Messenger bridge.
- **DeltaFriends:** Provides a directory for users to share their address and biography.
- **GroupMaster:** Extends the capabilities of Delta Chat groups, adding "mega groups", "channels", and allowing to have public groups, or invite friends to join a group with a private link.
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

It will listen for incoming messages and handle them with plugins.

Install `Delta Chat  <https://delta.chat>`_ and add your bot's email address as a contact and
start chatting with it! You can also add the bot as a member to a group chat.


Delta Chat Bot Integration (Request)
====================================

Bot API
-------

- Delta Chat Core (**DCC**) must provide functions to declare the configured account as bot, and to know if a contact is a bot. If an account is a bot, **DCC** must include a header in the messages sent so other **DC clients** know this is a bot account.
- **DC clients** applications should show a label or other prominent way to identify an account as a bot.
- **DCC** must allow to register a list of commands and their description, this information is sent attached to the message sent by the bot, **DC clients** should use this information to provide command completion and description.
- For consistency **DCC** should force a command prefix for bots instead of letting this decision to bots developers (ex. "!" or "/")
- When the bot or a new member is added to a group the bot's **DCC** must automatically reply with a message with the metadata about the commands the bot supports. **DC clients** shouldn't show this message to the user or show a system message instead.
- By default bots should be added to groups in a **"privacy mode"**, in this mode **DC clients** will not send messages to the bot unless they are command messages or changes in the group status (ex. adding/removing members, changing group name or picture). This way the bots are not overloaded with useless messages and also improves the privacy for users.
- **DC clients** must provide a way to know if a bot is in "privacy mode" or not in the group settings, and allow to change the mode (only if the bot require it for some functionality, if the bot don't require "privacy mode" to be off, don't let the user change this).
- Bots should not receive messages from other bots, if a bot sends a message to a group, **DCC** should send the message to the human members of the group, unless it is a  change in group status (ex. adding/removing members, changing group name or picture)
- On a private chat(1x1) with the bot, the bot may send an especial message to send a "buttons" list, each button has a label, a command string and a "has_args" flag, with this data, **DC clients** should display a board with the buttons in the bot's chat, when a button is clicked, if "has_args" is false, a message with the button's command should be sent, otherwise the DC client should show the input field in an especial way with some visual effects to reflect that what you type here will be sent as part of the command, the user type what should be passed to the command and then press the sent button.


Games API
---------

- **TODO:** talk here about an integrated webview in DC clients, and an API for intercommunication between the webview(JavaScript) and DCC
- Messages sent in background with the game api should be differentiated from messages sent manually by the user
- Background messages can only include the bot address in the "To" header (ex. clients can't be used to send spam to 3rd parties)
