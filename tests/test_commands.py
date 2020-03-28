
import pytest

from deltabot.commands import parse_command_docstring


def test_parse_command_docstring():
    with pytest.raises(ValueError):
        parse_command_docstring(lambda: None)

    def func(command):
        """short description.

        long description.
        """
    short, long = parse_command_docstring(func)
    assert short == "short description."
    assert long == "long description."
