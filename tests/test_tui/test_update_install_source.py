"""TUI update copy must reinstall from GitHub, not the PyPI package name."""

from unittest.mock import Mock, patch

from polyterm.tui.menu import MainMenu
from polyterm.tui.screens.settings import update_polyterm
from polyterm.utils.install_source import GITHUB_PIPX_SPEC


def _printed_text(console):
    return "\n".join(str(call.args[0]) if call.args else "" for call in console.print.call_args_list)


def test_menu_check_for_updates_does_not_query_pypi():
    import polyterm.tui.menu as menu_mod

    menu = MainMenu()
    indicator, latest = menu.check_for_updates()

    assert indicator == ""
    assert latest == ""
    assert not hasattr(menu_mod, "requests")


def test_settings_update_failure_copy_uses_github_not_pypi_package_name():
    console = Mock()
    console.input.return_value = ""

    with patch(
        "polyterm.utils.install_source.reinstall_from_github",
        return_value=(False, "pipx", "boom"),
    ):
        result = update_polyterm(console)

    assert result is False
    output = _printed_text(console)
    assert "PyPI is decommissioned" in output
    assert GITHUB_PIPX_SPEC in output
    assert "pipx install polyterm" not in output
    assert "pipx upgrade polyterm" not in output
    assert "pip install --upgrade polyterm" not in output


def test_settings_update_success_reinstalls_from_github_without_pypi():
    console = Mock()
    console.input.return_value = "n"

    with patch(
        "polyterm.utils.install_source.reinstall_from_github",
        return_value=(True, "pipx", ""),
    ) as mock_reinstall:
        result = update_polyterm(console)

    assert result is False
    mock_reinstall.assert_called_once()
    output = _printed_text(console)
    assert "Reinstalled from GitHub main" in output
    assert "pipx install polyterm" not in output
