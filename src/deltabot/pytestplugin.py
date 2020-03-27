
import pytest


@pytest.fixture
def testbot():
    class TestBot:
        # def make_command(text):
        #    return BotCommand.parse_from_text(text)
        pass
    return TestBot()
