.PHONY: all
all: simplebot friends getdelta groupmaster help tictactoe webgrabber wikiquote xkcd

.PHONY: simplebot
simplebot:
	echo y | pip uninstall simplebot; pip install .

.PHONY: friends
friends:
	echo y | pip uninstall simplebot_friends; pip install plugins/simplebot_friends

.PHONY: getdelta
getdelta:
	echo y | pip uninstall simplebot_getdelta; pip install plugins/simplebot_getdelta

.PHONY: groupmaster
groupmaster:
	echo y | pip uninstall simplebot_groupmaster; pip install plugins/simplebot_groupmaster

.PHONY: help
help:
	echo y | pip uninstall simplebot_help; pip install plugins/simplebot_help

.PHONY: tictactoe
tictactoe:
	echo y | pip uninstall simplebot_tictactoe; pip install plugins/simplebot_tictactoe

.PHONY: translators
translators:
	echo y | pip uninstall simplebot_translators; pip install plugins/simplebot_translators

.PHONY: webgrabber
webgrabber:
	echo y | pip uninstall simplebot_webgrabber; pip install plugins/simplebot_webgrabber

.PHONY: wikiquote
wikiquote:
	echo y | pip uninstall simplebot_wikiquote; pip install plugins/simplebot_wikiquote

.PHONY: xkcd
xkcd:
	echo y | pip uninstall simplebot_xkcd; pip install plugins/simplebot_xkcd
