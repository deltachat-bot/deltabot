Delta.Chat example bot
======================

A simple example "deltabot" that receives and sends messages
for an e-mail account.  It will reply to messages
to it by echoing them back. It works as part
of a group or in 1:1 chats in https://delta.chat
applications (or even with regular email) and will
also reply to regular e-mails.  Deltabot supports
Autocrypt end-to-end encryption but note that the operator
of the "bot" service can look into messages that are
sent to it.


install
-------

To install make sure you have
`the python deltachat-bindings <https://py.delta.chat>`_
installed, at best in a ``virtualenv`` environment .
Then install the bot::

    pip install deltabot


starting the bot
----------------

First you need to provide an emailaddress and a password
to allow the bot to receive and send messages for that
address::

    deltabot init email@example.org password123

This command will try to contact the imap/smtp servers
for ``example.org`` and logging in with the given e-mail
address and password.  Once this successfully completes,
initialization is done and tested.

You can then let the bot listen continously::

    deltabot serve

It will listen for incoming messages and reply to each of them.

To see some action install https://delta.chat and add
your bot-email address as a contact and start chatting
with it! You can also add the bot as a member to a group chat.

Looking at the code
-------------------

Checkout this file which contains the definition of
a command line client used above, and its interaction
with the bindings (``src/deltabot/cmdline.py``):

https://github.com/deltachat/deltabot/blob/master/src/deltabot/cmdline.py

