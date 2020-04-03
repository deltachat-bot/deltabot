
import pytest


@pytest.fixture
def parser(plugin_manager):
    from deltabot.parser import get_base_parser
    return get_base_parser(plugin_manager)


class TestParser:
    def test_generic(self, parser):
        args = parser.main_parse_argv(["deltabot"])
        assert args.command is None
        assert not args.version
        assert args.verbose == 0

        args = parser.main_parse_argv(["deltabot", "--version"])
        assert args.version

        args = parser.main_parse_argv(["deltabot", "--verbose"])
        assert args.verbose == 1

        args = parser.main_parse_argv(["deltabot", "--basedir=123"])
        assert args.basedir == "123"


class TestInit:
    def test_noargs(self, parser):
        with pytest.raises(SystemExit) as ex:
            parser.main_parse_argv(["deltabot", "init"])
        assert ex.value.code != 0

    def test_basic_args(self, parser):
        args = parser.main_parse_argv(["deltabot", "init", "email@x.org", "123"])
        assert args.command == "init"
        assert args.emailaddr == "email@x.org"
        assert args.password == "123"

    def test_arg_verification_fails(self, parser):
        args = parser.main_parse_argv(["deltabot", "init", "email", "123"])
        assert args.command == "init"
        assert args.emailaddr == "email"
        assert args.password == "123"
        with pytest.raises(SystemExit) as ex:
            parser.main_run(bot=None, args=args)
        assert ex.value.code != 0

    def test_arg_run_fails(self, parser):
        args = parser.main_parse_argv(["deltabot", "init", "email@example.org", "123"])
        l = []

        class PseudoBot:
            def perform_configure_address(self, emailaddr, password):
                l.append((emailaddr, password))
                return True
        parser.main_run(bot=PseudoBot(), args=args)
        assert l == [("email@example.org", "123")]
