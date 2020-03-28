

def test_builtin_plugins(mock_bot):
    assert "deltabot.builtin.echo" in mock_bot.plugins.dict()
    mock_bot.plugins.remove(name="deltabot.builtin.echo")
    assert "deltabot.builtin.echo" not in mock_bot.plugins.dict()
