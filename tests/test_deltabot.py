
import pytest


def test_parse_command_docstring():
    from deltabot.deltabot import parse_command_docstring
    with pytest.raises(ValueError):
        parse_command_docstring(lambda: None)

    def func(command):
        """short description.

        long description.
        """
    short, long = parse_command_docstring(func)
    assert short == "short description."
    assert long == "long description."


def test_builtin_plugins(mock_bot):
    assert "deltabot.builtin.echo" in mock_bot.list_plugins()
    mock_bot.remove_plugin(name="deltabot.builtin.echo")
    assert "deltabot.builtin.echo" not in mock_bot.list_plugins()
