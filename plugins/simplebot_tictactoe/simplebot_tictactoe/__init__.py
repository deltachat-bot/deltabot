# -*- coding: utf-8 -*-
from enum import IntEnum
import gettext
import os
import sqlite3

from simplebot import Plugin, PluginCommand
from jinja2 import Environment, PackageLoader, select_autoescape


class Status(IntEnum):
    INVITED = -1
    FINISHED = 0
    PLAYING = 1


class TicTacToe(Plugin):

    name = 'Tic Tac Toe'
    version = '0.1.0'

    @classmethod
    def activate(cls, bot):
        super().activate(bot)

        cls.env = Environment(
            loader=PackageLoader(__name__, 'templates'),
            autoescape=select_autoescape(['html', 'xml'])
        )

        cls.db = DBManager(os.path.join(
            cls.bot.get_dir(__name__), 'tictactoe.db'))

        localedir = os.path.join(os.path.dirname(__file__), 'locale')
        lang = gettext.translation('simplebot_echo', localedir=localedir,
                                   languages=[bot.locale], fallback=True)
        lang.install()

        cls.description = _('Tic Tac Toe game to play with friends')
        cls.commands = [
            PluginCommand('/toe/play', ['[email]'],
                          _('Invite a friend to play or accept an invitation to play.'), cls.play_cmd),
            PluginCommand('/toe/surrender', [],
                          _('End the game in the group it is sent.'), cls.surrender_cmd),
            PluginCommand(
                '/toe/new', [], _('Start a new game in the current game group.'), cls.new_cmd),
            PluginCommand('/toe/move', ['<id>', '<cell>'],
                          _('Move to the given cell in the game with the given id.'), cls.move_cmd)]
        cls.bot.add_commands(cls.commands)

    @classmethod
    def deactivate(cls):
        super().deactivate()
        cls.db.close()

    @classmethod
    def run_turn(cls, chat, players, ctx):
        game = cls.db.execute(
            'SELECT * FROM games WHERE players=?', (players,), 'one')
        b = Board(game['board'])
        p1, p2 = game['players'].split(',')
        winner = b.get_winner()
        if winner is not None:
            cls.db.execute('UPDATE games SET status=? WHERE players=?',
                           (Status.FINISHED, game['players']))
            if winner == '-':
                chat.send_text(
                    _('Game over.\nIt is a draw!\n\n{}').format(b.pretty_str()))
            else:
                winner = p1 if p1 != game['turn'] else p2
                chat.send_text(_('Game over.\n{} Wins!!!\n\n{}').format(
                    winner, b.pretty_str()))
        else:
            priv_chat = cls.bot.get_chat(game['turn'])
            bot_addr = cls.bot.get_address()
            board = list(enumerate(b.board))
            board = [board[:3], board[3:6], board[6:]]
            html = cls.env.get_template('index.html').render(
                plugin=cls, bot_addr=bot_addr, gid=chat.id, board=board)
            cls.bot.send_html(priv_chat, html, cls.name,
                              chat.get_name(), ctx.mode)
            chat.send_text(
                _('{} is your turn...\n\n{}').format(game['turn'], b.pretty_str()))

    @classmethod
    def play_cmd(cls, ctx):
        if ctx.text:  # inviting someone to play
            p1 = ctx.msg.get_sender_contact().addr
            p2 = ctx.text
            if p1 == p2:
                chat = cls.bot.get_chat(ctx.msg)
                chat.send_text(_("You can't play with yourself"))
                return
            players = ','.join(sorted([p1, p2]))
            game = cls.db.execute(
                'SELECT * FROM games WHERE players=?', (players,), 'one')
            if game is None:  # first time playing with p2
                chat = cls.bot.create_group(
                    '❎ {} Vs {} [{}]'.format(p1, p2, cls.name), [ctx.msg.get_sender_contact(), p2])
                cls.db.insert(
                    (players, chat.id, Status.INVITED, p1, str(Board()), p1))
                chat.send_text(
                    _('Hello {},\nYou had been invited by {} to play {}, to start playing send a message in this group with the command:\n/toe/play').format(p2, p1, cls.name))
            else:
                chat = cls.bot.get_chat(ctx.msg)
                chat.send_text(
                    _('You already has a game group with {}, to start a new game just go to the game group and send:\n/toe/new').format(p2))
        else:    # accepting a game
            p2 = ctx.msg.get_sender_contact().addr
            chat = cls.bot.get_chat(ctx.msg)
            game = cls.db.execute(
                'SELECT * FROM games WHERE gid=?', (chat.id,), 'one')
            orig_p2 = [p for p in game['players'].split(
                ',') if p != game['x']][0]
            if game is None or p2 != orig_p2:
                chat.send_text(
                    _('You are not allowed to do that, if you are trying to invite a new friend, please provide the email of the friend you want to play with'))
            # accept the invitation and start playing
            elif game['status'] == Status.INVITED:
                cls.db.execute('UPDATE games SET status=? WHERE players=?',
                               (Status.PLAYING, game['players']))
                chat = cls.bot.get_chat(ctx.msg)
                chat.send_text(_('Game started!'))
                cls.run_turn(chat, game['players'], ctx)
            else:  # p2 already accepted the game
                chat = cls.bot.get_chat(ctx.msg)
                chat.send_text(
                    _('You alredy accepted to play. To start a new game use /toe/new'))

    @classmethod
    def surrender_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        loser = ctx.msg.get_sender_contact().addr
        game = cls.db.execute(
            'SELECT * FROM games WHERE gid=?', (chat.id,), 'one')
        # this is not your game group
        if game is None or loser not in game['players'].split(','):
            chat.send_text(
                _('This is not your game group, please send that command in the game group you want to surrender'))
        elif game['status'] != Status.FINISHED:
            p1, p2 = game['players'].split(',')
            x = p1 if p1 != loser else p2
            cls.db.execute('UPDATE games SET status=?, turn=?, x=? WHERE players=?',
                           (Status.FINISHED, x, x, game['players']))
            chat.send_text(_('Game Over.\n{} Wins!!!').format(game['turn']))
        else:
            chat.send_text(
                _('There are no game running. To start a new game use /toe/new'))

    @classmethod
    def new_cmd(cls, ctx):
        chat = cls.bot.get_chat(ctx.msg)
        sender = ctx.msg.get_sender_contact().addr
        game = cls.db.execute(
            'SELECT * FROM games WHERE gid=?', (chat.id,), 'one')
        # this is not your game group
        if game is None or sender not in game['players'].split(','):
            chat.send_text(
                _('This is not your game group, please send that command in the game group you want to start a new game'))
        elif game['status'] == Status.FINISHED:
            p1, p2 = game['players'].split(',')
            x = p1 if p1 != game['x'] else p2
            cls.db.execute('UPDATE games SET status=?, turn=?, x=?, board=? WHERE players=?',
                           (Status.PLAYING, x, x, str(Board()), game['players']))
            chat = cls.bot.get_chat(ctx.msg)
            chat.send_text(_('Game started!'))
            cls.run_turn(chat, game['players'], ctx)
        else:
            chat.send_text(
                _('There are a game running already, to start a new one first end this game or surrender'))

    @classmethod
    def move_cmd(cls, ctx):
        chat_id, pos = map(int, ctx.text.split())
        player = ctx.msg.get_sender_contact().addr
        game = cls.db.execute(
            'SELECT * FROM games WHERE gid=?', (chat_id,), 'one')
        if game is not None and player == game['turn']:
            p1, p2 = game['players'].split(',')
            board = Board(game['board'])
            sign = 'x' if player == game['x'] else 'o'
            try:
                board.move(sign, pos)
                turn = p1 if p1 != player else p2
                cls.db.execute('UPDATE games SET turn=?, board=? WHERE players=?', (turn, str(
                    board), game['players']))
                chat = cls.bot.get_chat(chat_id)
                cls.run_turn(chat, game['players'], ctx)
            except InvalidMove:
                chat = cls.bot.get_chat(ctx.msg)
                chat.send_text(_('Invalid move!'))
        else:
            chat = cls.bot.get_chat(ctx.msg.get_sender_contact())
            chat.send_text(
                _("It's NOT your turn, please wait the other player to move"))


class Board:
    def __init__(self, board_str=None):
        if board_str is None:
            self.board = [' ']*9
        else:
            self.board = board_str.split(',')

    def __str__(self):
        return ','.join(self.board)

    def get_winner(self):
        b = self.board
        rows = [(b[0], b[4], b[8]),
                (b[1], b[4], b[7]),
                (b[2], b[4], b[6]),
                (b[3], b[4], b[5]),
                (b[0], b[1], b[2]),
                (b[0], b[3], b[6]),
                (b[6], b[7], b[8]),
                (b[2], b[5], b[8])]
        if ('x',)*3 in rows:
            return 'x'
        elif ('o',)*3 in rows:
            return 'o'
        elif ' ' not in self.board:
            return '-'
        return None

    def move(self, sign, pos):
        if pos < len(self.board) and self.board[pos] == ' ':
            self.board[pos] = sign
        else:
            raise InvalidMove()

    def pretty_str(self):
        text = '{}{}{}\n{}{}{}\n{}{}{}'.format(*self.board)
        text = text.replace('x', '❎')
        text = text.replace('o', '🅾')
        return text.replace(' ', '⬜')


class InvalidMove(Exception):
    def __init__(self):
        super().__init__()


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path)
        self.db.row_factory = sqlite3.Row
        self.execute('''CREATE TABLE IF NOT EXISTS games
                        (players TEXT NOT NULL,
                         gid INTEGER NOT NULL, 
                         status INTEGER NOT NULL,
                         turn TEXT NOT NULL,
                         board TEXT NOT NULL,
                         x TEXT NOT NULL,
                         PRIMARY KEY(players))''')

    def execute(self, statement, args=(), get='all'):
        with self.db:
            r = self.db.execute(statement, args)
            return r.fetchall() if get == 'all' else r.fetchone()

    def insert(self, row):
        self.execute('INSERT INTO games VALUES (?,?,?,?,?,?)', row)

    def close(self):
        self.db.close()
