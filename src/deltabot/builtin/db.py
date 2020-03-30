
import os
import sqlite3
from deltabot.hookspec import deltabot_hookimpl


@deltabot_hookimpl
def deltabot_init(bot):
    db_path = os.path.join(os.path.dirname(bot.account.db_path), "bot.db")
    bot.plugins.add_module("db", DBManager(db_path))


class DBManager:
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._execute('''CREATE TABLE IF NOT EXISTS peerprefs
                        (addr TEXT PRIMARY KEY,
                         locale TEXT,
                         mode INTEGER)''')
        self._execute('''CREATE TABLE IF NOT EXISTS config
                        (keyname TEXT PRIMARY KEY,
                         value TEXT)''')

    def _execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    @deltabot_hookimpl
    def deltabot_store_setting(self, key, value):
        old_val = self.deltabot_get_setting(key)
        self._execute('INSERT INTO config VALUES (?,?)', (key, value))
        return old_val

    @deltabot_hookimpl
    def deltabot_get_setting(self, key):
        row = self._execute(
            'SELECT * FROM config WHERE keyname=?',
            (key,),
        ).fetchone()
        return row['value'] if row else None

    @deltabot_hookimpl
    def deltabot_shutdown(self, bot):
        self.db.close()


class TestDB:
    def test_settings(self, mock_bot):
        mock_bot.store_setting("hello", "world")
        assert mock_bot.get_setting("hello") == "world"
