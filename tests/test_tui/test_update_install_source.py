"""TUI update copy must reinstall from GitHub, not the PyPI package name."""

from io import StringIO
from unittest.mock import Mock, patch

from rich.console import Console

from polyterm.tui.menu import MainMenu
from polyterm.tui.screens.settings import update_polyterm
from polyterm.utils.github_update import GITHUB_RELEASES_LATEST_URL
from polyterm.utils.install_source import GITHUB_PIPX_SPEC


def _printed_text(console):
    return "\n".join(str(call.args[0]) if call.args else "" for call in console.print.call_args_list)


def test_menu_check_for_updates_does_not_query_pypi():
    import polyterm.tui.menu as menu_mod

    captured = []

    def get_json(url):
        captured.append(url)
        return {"tag_name": "v0.11.0"}

    menu = MainMenu()
    with patch("polyterm.__version__", "0.10.0"), patch(
        "polyterm.utils.github_update._get_json",
        side_effect=get_json,
    ):
        indicator, latest = menu.check_for_updates()

    assert latest == "0.11.0"
    assert "v0.11.0" in indicator
    assert captured == [GITHUB_RELEASES_LATEST_URL]
    assert all("pypi.org" not in url for url in captured)
    assert not hasattr(menu_mod, "requests")


def test_menu_check_for_updates_newer_github_tag():
    menu = MainMenu()
    with patch("polyterm.__version__", "0.10.0"), patch(
        "polyterm.utils.github_update.newer_github_version",
        return_value="0.11.0",
    ):
        indicator, latest = menu.check_for_updates()

    assert latest == "0.11.0"
    assert "Update Available" in indicator
    assert "v0.11.0" in indicator


def test_menu_check_for_updates_already_current():
    menu = MainMenu()
    with patch("polyterm.__version__", "0.11.0"), patch(
        "polyterm.utils.github_update.newer_github_version",
        return_value=None,
    ):
        indicator, latest = menu.check_for_updates()

    assert indicator == ""
    assert latest == ""


def test_menu_check_for_updates_network_error():
    menu = MainMenu()
    with patch(
        "polyterm.utils.github_update.newer_github_version",
        side_effect=OSError("network down"),
    ):
        indicator, latest = menu.check_for_updates()

    assert indicator == ""
    assert latest == ""


def test_menu_check_for_updates_caches_session():
    menu = MainMenu()
    with patch(
        "polyterm.utils.github_update.newer_github_version",
        return_value="0.11.0",
    ) as mock_check:
        first = menu.check_for_updates()
        second = menu.check_for_updates()

    assert mock_check.call_count == 1
    assert first == second
    assert first[1] == "0.11.0"


def test_menu_display_shows_update_row_when_newer():
    menu = MainMenu()
    menu._update_cache = (
        " [bold green]🔄 Update Available: v0.11.0[/bold green]",
        "0.11.0",
    )
    buf = StringIO()
    menu.console = Console(file=buf, force_terminal=True, width=120, color_system=None)
    menu.display()
    output = buf.getvalue()

    assert "Update Available: v0.11.0" in output
    assert "Update to v0.11.0" in output


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
