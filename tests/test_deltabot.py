import pytest



def test_help(cmd):
    cmd.run_ok([], """
        *bot management*
        *init*
        *serve*
    """)
