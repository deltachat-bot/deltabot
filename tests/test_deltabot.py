

def test_builtin_plugins(mock_bot):
    assert "deltabot.builtin.echo" in mock_bot.list_plugins()
    mock_bot.remove_plugin(name="deltabot.builtin.echo")
    assert "deltabot.builtin.echo" not in mock_bot.list_plugins()
