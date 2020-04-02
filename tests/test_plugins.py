
import deltabot
from deltabot.plugins import get_global_plugin_manager


def test_globality_plugin_manager(monkeypatch):
    monkeypatch.setattr(deltabot.plugins, "_pm", None)
    pm1 = get_global_plugin_manager()
    pm2 = get_global_plugin_manager()
    assert pm1 == pm2
    monkeypatch.undo()
    assert pm1 != get_global_plugin_manager()


def test_builtin_plugins(mock_bot):
    assert ".builtin.echo" in mock_bot.plugins.dict()
    mock_bot.plugins.remove(name=".builtin.echo")
    assert ".builtin.echo" not in mock_bot.plugins.dict()
