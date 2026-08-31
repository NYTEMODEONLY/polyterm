"""Tests for polyterm update (GitHub reinstall, PyPI decommissioned)."""

import re
from unittest.mock import patch

from click.testing import CliRunner

from polyterm.cli.main import cli
from polyterm.utils.install_source import GITHUB_PIPX_SPEC


def _plain(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*m", "", text)


def test_update_reinstalls_from_github_and_does_not_query_pypi():
    runner = CliRunner()

    with patch("polyterm.utils.install_source.subprocess.run") as mock_run:
        mock_run.side_effect = [
            type("Result", (), {"returncode": 0})(),
            type("Result", (), {"returncode": 0, "stdout": "ok", "stderr": ""})(),
        ]
        result = runner.invoke(cli, ["update"], input="y\n")

    output = _plain(result.output)
    assert result.exit_code == 0
    assert "GitHub is the source of truth" in output
    assert "PyPI is decommissioned" in output
    assert "pipx install polyterm" not in output
    assert "pipx upgrade polyterm" not in output
    assert "pypi.org" not in output
    install_cmd = mock_run.call_args_list[1][0][0]
    assert install_cmd == ["pipx", "install", "--force", GITHUB_PIPX_SPEC]


def test_update_failure_copy_uses_github_git_spec():
    runner = CliRunner()

    with patch("polyterm.utils.install_source.reinstall_from_github") as mock_reinstall:
        mock_reinstall.return_value = (False, "pipx", "boom")
        result = runner.invoke(cli, ["update"], input="y\n")

    output = _plain(result.output)
    assert result.exit_code == 0
    assert "Update failed" in output
    assert GITHUB_PIPX_SPEC in output
    assert "pipx install polyterm" not in output
    assert "pipx upgrade polyterm" not in output
