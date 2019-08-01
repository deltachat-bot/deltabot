# -*- coding: utf-8 -*-
import gettext
import os
import sqlite3

from simplebot import Plugin
from deltachat.chatting import Chat
from jinja2 import Environment, PackageLoader, select_autoescape


class TicTacToe(Plugin):

    name = 'Tic Tac Toe'
    version = '0.1.0'
    author = 'adbenitez'
    author_email = 'adbenitez@nauta.cu'
    cmd = '!toe'
    INVITED_STATUS = -1
    FINISHED_STATUS = 0
    PLAYING_STATUS = 1

    @classmethod
    def activate(cls, ctx):
        super().activate(ctx)
        cls.TEMP_FILE = os.path.join(cls.ctx.basedir, cls.name+'.html')
        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )
        cls.conn = sqlite3.connect(
            os.path.join(cls.ctx.basedir, 'tictactoe.db'))
        with cls.conn:
            cls.conn.execute('''CREATE TABLE IF NOT EXISTS games
                                (p1 TEXT NOT NULL, p2 TEXT NOT NULL, gid INTEGER NOT NULL, status INTEGER NOT NULL,
                                 turn TEXT NOT NULL,  board TEXT NOT NULL, x TEXT NOT NULL, PRIMARY KEY(p1, p2))''')

        # localedir = os.path.join(os.path.dirname(__file__), 'locale')
        # try:
        #     lang = gettext.translation('simplebot_echo', localedir=localedir,
        #                                languages=[ctx.locale])
        # except OSError:
        #     lang = gettext.translation('simplebot_echo', localedir=localedir,
        #                                languages=['en'])
        # lang.install()
        # cls.description = _('plugin-description')
        # cls.long_description = _('plugin-long-description')

    @classmethod
    def process(cls, msg):
        for cmd, action in [('!toe!move', cls.move_cmd), ('!toe!play', cls.play_cmd), ('!toe!surrender', cls.surrender_cmd),
                            ('!toe!new', cls.new_cmd), ('!toe', cls.help_cmd)]:
            arg = cls.get_args(cmd, msg.text)
            if arg is not None:
                action(msg, arg)
                break
        else:
            return False
        return True

    @classmethod
    def run_turn(cls, chat, game):
        board = Board(game[5])
        winner = board.get_winner()
        if winner is not None:
            game[3] = cls.FINISHED_STATUS
            with cls.conn:
                cls.conn.execute(
                    'REPLACE INTO games VALUES (?,?,?,?,?,?,?)', game)
            if winner == '-':
                chat.send_text(
                    'Game over.\nIt is a match!\n\n{}'.format(board.pretty_str()))
            else:
                chat.send_text('Game over.\n{} Wins!!!\n\n{}'.format(
                    game[4], board.pretty_str()))
        else:
            priv_chat = cls.ctx.acc.create_chat_by_contact(
                cls.ctx.acc.create_contact(game[4]))
            # TODO: send html board
            priv_chat.send_text(Board(game[5]).pretty_str())
            chat.send_text('Player {} is turn...'.format(game[4]))

    @classmethod
    def play_cmd(cls, msg, arg):
        arg = arg.strip()
        if arg:  # inviting someone to play
            p1 = msg.get_sender_contact().addr
            p2 = arg
            game = cls.conn.execute(
                'SELECT * FROM games WHERE p1=? AND p2=?', (p1, p2)).fetchone()
            if game is None:  # first time playing with p2
                chat = cls.ctx.acc.create_group_chat(
                    '{} Vs {} [{}]'.format(p1, p2, cls.name))
                chat.add_contact(msg.get_sender_contact())
                chat.add_contact(cls.ctx.acc.create_contact(p2))
                with cls.conn:
                    cls.conn.execute('INSERT INTO games VALUES (?,?,?,?,?,?,?)',
                                     (p1, p2, chat.id, cls.INVITED_STATUS, p1, str(Board()), p1))
                chat.send_text('Hello {},\nYou had been invited by {} to play {}, to start playing send a message in this group with the command:\n!toe!play'.format(
                    p2, p1, cls.name))
            else:
                chat = cls.ctx.acc.create_chat_by_contact(
                    msg.get_sender_contact())
                chat.send_text(
                    'You already invited {} to play {}, to start a new game just go to the game group and send:\n!toe!new'.format(p2, cls.name))
        else:    # accepting a game
            p2 = msg.get_sender_contact().addr
            chat = cls.ctx.acc.create_chat_by_message(msg)
            game = cls.conn.execute(
                'SELECT * FROM games WHERE gid=? AND p2=?', (chat.id, p2)).fetchone()
            if game is None:  # this is not your game group
                chat.send_text(
                    'This is not your game group, if you are trying to play a new game, please supply the email of the friend you want to play with')
            elif game[3] == cls.INVITED_STATUS:  # accept the invitation and start playing
                game = list(game)
                game[3] = cls.PLAYING_STATUS
                with cls.conn:
                    cls.conn.execute(
                        'REPLACE INTO games VALUES (?,?,?,?,?,?,?)', game)
                chat = cls.ctx.acc.create_chat_by_message(msg)
                chat.send_text('Game started!\nGroup id:{}'.format(chat.id))
                cls.run_turn(chat, game)
            else:  # p2 already accepted the game
                chat = cls.ctx.acc.create_chat_by_message(msg)
                chat.send_text(
                    'You alredy accepted to play. To start a new game use !toe!new')

    @classmethod
    def surrender_cmd(cls, msg, arg):
        chat = msg.create_chat_by_message(msg)
        game = cls.conn.execute(
            'SELECT * FROM games WHERE gid=?', (chat.id,)).fetchone()
        if game is None:  # this is not your game group
            chat.send_text(
                'This is not your game group, please send that command in the game group you want to surrender')
        elif game[3] != cls.FINISHED_STATUS:
            game = list(game)
            game[3] = cls.FINISHED_STATUS
            game[4] = game[6] = game[0] if game[0] != game[6] else game[1]
            with cls.conn:
                cls.conn.execute(
                    'REPLACE INTO games VALUES (?,?,?,?,?,?,?)', game)
            chat.send_text('{} Wins!!!'.format(game[4]))
        else:
            chat.send_text(
                'There are no game running. To start a new game use !toe!new')

    @classmethod
    def new_cmd(cls, msg, arg):
        chat = msg.create_chat_by_message(msg)
        game = cls.conn.execute(
            'SELECT * FROM games WHERE gid=?', (chat.id,)).fetchone()
        if game is None:  # this is not your game group
            chat.send_text(
                'This is not your game group, please send that command in the game group you want to start a new game')
        elif game[3] == cls.FINISHED_STATUS:
            game = list(game)
            game[3] = cls.PLAYING_STATUS
            game[4] = game[6] = game[0] if game[0] != game[6] else game[1]
            game[5] = str(Board())
            with cls.conn:
                cls.conn.execute(
                    'REPLACE INTO games VALUES (?,?,?,?,?,?,?)', game)
            chat = cls.ctx.acc.create_chat_by_message(msg)
            chat.send_text('Game started!')
            cls.run_turn(chat, game)
        else:
            chat.send_text(
                'There are a game running already, to start a new one first end this game or surrender')

    @classmethod
    def move_cmd(cls, msg, arg):
        chat_id, pos = map(int, arg.split())
        player = msg.get_sender_contact().addr
        game = cls.conn.execute(
            'SELECT * FROM games WHERE gid=?', (chat_id,)).fetchone()
        if game is not None and player == game[4]:
            game = list(game)
            board = Board(game[5])
            sign = 'x' if player == game[6] else 'o'
            try:
                board.move(sign, pos)
                game[4] = game[0] if game[1] == player else game[1]
                game[5] = str(board)
                with cls.conn:
                    cls.conn.execute(
                        'REPLACE INTO games VALUES (?,?,?,?,?,?,?)', game)
                chat = Chat(cls.ctx.acc._dc_context, chat_id)
                cls.run_turn(chat, game)
            except InvalidMove:
                chat = cls.ctx.acc.create_chat_by_contact(
                    msg.get_sender_contact())
                chat.send_text('Invalid move!')
        else:
            chat = cls.ctx.acc.create_chat_by_contact(msg.get_sender_contact())
            chat.send_text(
                "It's NOT your turn, please wait the other player to move")

    @classmethod
    def help_cmd(cls, msg, arg):
        chat = cls.ctx.acc.create_chat_by_message(msg)
        chat.send_text('to do')


class Board:
    def __init__(self, board_str=None):
        if board_str is None:
            self._board = [' ']*9
        else:
            self._board = board_str.split(',')

    def __str__(self):
        return ','.join(self._board)

    def get_winner(self):
        b = self._board
        if b[0] == b[4] == b[8] or b[1] == b[4] == b[7] or b[2] == b[4] == b[6] or b[3] == b[4] == b[5]:
            return b[4]
        elif b[0] == b[1] == b[2] or b[0] == b[3] == b[6]:
            return b[0]
        elif b[6] == b[7] == b[8] or b[2] == b[5] == b[8]:
            return b[8]
        elif ' ' not in self._board:
            return '-'
        return None

    def move(self, sign, pos):
        if pos < len(self._board) and self._board[pos] == ' ':
            self._board[pos] = sign
        else:
            raise InvalidMove()

    def pretty_str(self):
        return ' {}| {}| {}\n--+--+--\n {}| {}| {}\n--+--+--\n {}| {}| {}'.format(*self._board)


class InvalidMove(Exception):
    def __init__(self):
        super().__init__()
