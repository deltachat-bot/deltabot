import pytest
from _pytest.pytester import LineMatcher


class ClickRunner:
    def __init__(self, main):
        from click.testing import CliRunner
        self.runner = CliRunner()
        self._main = main
        self._rootargs = []

    def set_basedir(self, account_dir):
        self._rootargs.insert(0, "--basedir")
        self._rootargs.insert(1, account_dir)

    def run_ok(self, args, fnl=None, input=None):
        __tracebackhide__ = True
        argv = self._rootargs + args
        # we use our nextbackup helper to cache account creation
        # unless --no-test-cache is specified
        res = self.runner.invoke(self._main, argv, catch_exceptions=False,
                                 input=input)
        if res.exit_code != 0:
            print(res.output)
            raise Exception("cmd exited with %d: %s" % (res.exit_code, argv))
        return _perform_match(res.output, fnl)

    def run_fail(self, args, fnl=None, input=None, code=None):
        __tracebackhide__ = True
        argv = self._rootargs + args
        res = self.runner.invoke(self._main, argv, catch_exceptions=False,
                                 input=input)
        if res.exit_code == 0 or (code is not None and res.exit_code != code):
            print (res.output)
            raise Exception("got exit code {!r}, expected {!r}, output: {}".format(
                res.exit_code, code, res.output))
        return _perform_match(res.output, fnl)


def _perform_match(output, fnl):
    __tracebackhide__ = True
    if fnl:
        lm = LineMatcher(output.splitlines())
        lines = [x.strip() for x in fnl.strip().splitlines()]
        try:
            lm.fnmatch_lines(lines)
        except Exception:
            print(output)
            raise
    return output


@pytest.fixture
def cmd():
    """ invoke a command line subcommand. """
    from deltabot.cmdline import bot_main
    return ClickRunner(bot_main)


@pytest.fixture
def mycmd(cmd, tmpdir, request):
    cmd.set_basedir(tmpdir.mkdir("account").strpath)
    return cmd
