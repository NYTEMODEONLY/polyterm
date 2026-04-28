"""Inventory tests for every registered CLI command."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from polyterm.cli.main import cli


@pytest.mark.parametrize("command_name", sorted(cli.list_commands(None)))
def test_all_registered_commands_expose_help(command_name, monkeypatch, tmp_path):
    """Every command should import lazily and expose help without network access."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    runner = CliRunner()
    with runner.isolated_filesystem():
        monkeypatch.setattr("pathlib.Path.home", lambda: Path.cwd())
        result = runner.invoke(cli, [command_name, "--help"])

    assert result.exit_code == 0, result.output
    assert command_name in result.output
