

def test_general_help(cmd):
    cmd.run_ok([], """
        *bot management*
        *init*
        *serve*
    """)


class TestInit:
    def test_ok_then_info(self, mycmd, session_liveconfig):
        config = session_liveconfig.get(0)
        mycmd.run_ok(["--stdout-loglevel=info", "init", config["addr"], config["mail_pw"]], """
            *deltabot*INFO*Success*
        """)
        mycmd.run_ok(["info"], """
            *database_version*
        """)

    def test_fail_then_ok(self, mycmd, session_liveconfig):
        config = session_liveconfig.get(0)
        mycmd.run_fail(["--stdout-loglevel", "info", "init", config["addr"], "Wrongpw"], """
            *deltabot*ERR*
        """)
        mycmd.run_ok(["--stdout-loglevel=info", "init", config["addr"], config["mail_pw"]], """
            *deltabot*INFO*Success*
        """)


class TestPluginManagement:
    def test_list_plugins(self, mycmd):
        mycmd.run_ok(["list-plugins"], """
            *deltabot.builtin.echo*
        """)
