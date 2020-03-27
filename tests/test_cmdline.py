

def test_general_help(cmd):
    cmd.run_ok([], """
        *bot management*
        *init*
        *serve*
    """)


class TestInit:
    def test_basic(self, mycmd, session_liveconfig):
        config = session_liveconfig.get(0)
        mycmd.run_ok(["--stdout-loglevel", "info", "init", config["addr"], config["mail_pw"]], """
            *deltabot*INFO*success*
        """)
        mycmd.run_ok(["info"], """
            *database_version*
        """)


class TestPluginManagement:
    def test_list_plugins(self, mycmd):
        mycmd.run_ok(["list-plugins"], """
            *deltabot.builtin.echo*
        """)
