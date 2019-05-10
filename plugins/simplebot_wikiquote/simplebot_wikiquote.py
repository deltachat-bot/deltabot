# -*- coding: utf-8 -*-
import random

from simplebot import Plugin
import wikiquote as wq

class Wikiquote(Plugin):

    name = 'Wikiquote'
    description = 'Provides the !quote [text] command to get the quote of the day or a random quote from the given text. Ex. !quote Richard Stallman'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'

    @classmethod
    def process(cls, msg):
        arg = cls.get_args('!quote', msg.text)
        if arg is not None:
            if arg:
                pages = wq.search(arg)
                if pages:
                    author = random.choice(pages)
                    quote = '"%s"\n\n-- %s' % (random.choice(wq.quotes(author, max_quotes=40)), author)
                else:
                    quote = 'No quote found for:' + arg
            else:
                quote, author = wq.quote_of_the_day()
                quote = '"%s"\n\n-- %s' % (quote, author)
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text(quote)
            return True
        return False
