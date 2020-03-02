

def test_help(cmd):
    cmd.run_ok([], """
        *bot management*
        *init*
        *serve*
    """)


class TestInit:
    def test_basic(self, mycmd, session_liveconfig):
        config = session_liveconfig.get(0)
        mycmd.run_ok(["init", config["addr"], config["mail_pw"]], """
            *DeltaBot*INFO*success*
        """)
        mycmd.run_ok(["info"], """
            *database_version*
        """)
