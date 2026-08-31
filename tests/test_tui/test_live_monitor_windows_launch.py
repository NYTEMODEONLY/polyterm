"""Windows live-monitor second-terminal launch without a shell."""

from unittest.mock import Mock, patch

from polyterm.tui.screens import live_monitor as live_monitor_mod
from polyterm.tui.screens.live_monitor import (
    WINDOWS_CREATE_NEW_CONSOLE,
    launch_live_monitor,
    spawn_windows_live_monitor,
)


def test_spawn_windows_live_monitor_uses_list_args_without_shell():
    """Helper launches interpreter and script as separate argv items."""
    python = r"C:\Program Files\Python\python.exe"
    script = r"C:\Users\Test User\AppData\Local\Temp\polyterm_live_monitor.py"

    with patch.object(live_monitor_mod.subprocess, "Popen") as mock_popen:
        spawn_windows_live_monitor(python, script)

    mock_popen.assert_called_once()
    argv = mock_popen.call_args[0][0]
    kwargs = mock_popen.call_args.kwargs

    assert argv == [python, script]
    assert " " in argv[0]
    assert " " in argv[1]
    assert kwargs.get("shell") is False
    assert kwargs.get("creationflags") == WINDOWS_CREATE_NEW_CONSOLE
    assert kwargs.get("creationflags") == 0x00000010


def test_launch_live_monitor_win32_uses_helper_with_spaced_path(tmp_path, monkeypatch):
    """win32 launch mocks through the helper; spaces stay one argument."""
    spaced_dir = tmp_path / "My Temp Dir"
    spaced_dir.mkdir()
    monkeypatch.setattr(live_monitor_mod.sys, "platform", "win32")
    monkeypatch.setattr(live_monitor_mod.tempfile, "gettempdir", lambda: str(spaced_dir))

    mock_spawn = Mock(return_value=Mock())
    monkeypatch.setattr(live_monitor_mod, "spawn_windows_live_monitor", mock_spawn)

    launch_live_monitor(Mock(), category="crypto")

    mock_spawn.assert_called_once()
    python_executable, script_path = mock_spawn.call_args[0]
    assert python_executable == live_monitor_mod.sys.executable
    assert " " in script_path
    assert script_path.startswith(str(spaced_dir))
    assert mock_spawn.call_args.kwargs == {}


def test_launch_live_monitor_win32_popen_list_args_no_shell(tmp_path, monkeypatch):
    """End-to-end win32 branch: list argv, no shell, new-console flag."""
    spaced_dir = tmp_path / "user home"
    spaced_dir.mkdir()
    monkeypatch.setattr(live_monitor_mod.sys, "platform", "win32")
    monkeypatch.setattr(live_monitor_mod.tempfile, "gettempdir", lambda: str(spaced_dir))

    with patch.object(live_monitor_mod.subprocess, "Popen", return_value=Mock()) as mock_popen:
        launch_live_monitor(Mock(), market_id="abc123", market_title="Test Market")

    mock_popen.assert_called_once()
    argv = mock_popen.call_args[0][0]
    kwargs = mock_popen.call_args.kwargs

    assert isinstance(argv, list)
    assert argv[0] == live_monitor_mod.sys.executable
    assert len(argv) == 2
    assert " " in argv[1]
    assert argv[1].endswith(".py")
    assert kwargs.get("shell") is False
    assert kwargs.get("creationflags") == WINDOWS_CREATE_NEW_CONSOLE
