
from deltabot.bot import Replies


class TestReplies:
    def test_two_text(self, mock_bot):
        r = Replies(mock_bot.account)
        r.add(text="hello")
        r.add(text="world")
        l = list(r.get_reply_messages())
        assert len(l) == 2
        assert l[0].text == "hello"
        assert l[1].text == "world"

    def test_file(self, mock_bot, tmpdir):
        p = tmpdir.join("textfile")
        p.write("content")
        r = Replies(mock_bot.account)
        r.add(text="hello", filename=p.strpath)
        l = list(r.get_reply_messages())
        assert len(l) == 1
        assert l[0].text == "hello"
        s = open(l[0].filename).read()
        assert s == "content"
