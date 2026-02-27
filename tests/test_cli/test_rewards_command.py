"""CLI tests for rewards wallet-scoping behavior."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli


@patch("polyterm.cli.commands.rewards.Database")
@patch("polyterm.cli.main.Config")
def test_rewards_wallet_flag_scopes_position_query(mock_config_cls, mock_db_cls):
    """`rewards --wallet` should query open positions for that wallet only."""
    wallet = "0x" + "1" * 40
    mock_config = Mock()
    mock_config.get.return_value = None
    mock_config_cls.return_value = mock_config

    mock_db = Mock()
    mock_db.get_positions.return_value = []
    mock_db_cls.return_value = mock_db

    runner = CliRunner()
    result = runner.invoke(cli, ["rewards", "--wallet", wallet, "--format", "json"])

    assert result.exit_code == 0
    mock_db.get_positions.assert_called_once_with(status="open", wallet_address=wallet)
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["wallet"] == wallet
    assert payload["positions"] == []
    assert payload["positions_count"] == 0


@patch("polyterm.cli.commands.rewards.Database")
@patch("polyterm.cli.main.Config")
def test_rewards_saved_wallet_scopes_position_query(mock_config_cls, mock_db_cls):
    """Saved wallet config should scope rewards query when --wallet is not passed."""
    wallet = "0x" + "2" * 40
    mock_config = Mock()
    mock_config.get.return_value = wallet
    mock_config_cls.return_value = mock_config

    mock_db = Mock()
    mock_db.get_positions.return_value = []
    mock_db_cls.return_value = mock_db

    runner = CliRunner()
    result = runner.invoke(cli, ["rewards", "--format", "json"])

    assert result.exit_code == 0
    mock_db.get_positions.assert_called_once_with(status="open", wallet_address=wallet)
    payload = json.loads(result.output)
    assert payload["wallet"] == wallet
    assert payload["positions_count"] == 0


@patch("polyterm.cli.commands.rewards.Database")
@patch("polyterm.cli.main.Config")
def test_rewards_without_wallet_keeps_unscoped_query(mock_config_cls, mock_db_cls):
    """Without explicit or saved wallet, rewards should use unscoped open positions."""
    mock_config = Mock()
    mock_config.get.return_value = None
    mock_config_cls.return_value = mock_config

    mock_db = Mock()
    mock_db.get_positions.return_value = []
    mock_db_cls.return_value = mock_db

    runner = CliRunner()
    result = runner.invoke(cli, ["rewards", "--format", "json"])

    assert result.exit_code == 0
    mock_db.get_positions.assert_called_once_with(status="open")
    payload = json.loads(result.output)
    assert payload["wallet"] is None
    assert payload["positions_count"] == 0


@patch("polyterm.cli.commands.rewards.Database")
@patch("polyterm.cli.main.Config")
def test_rewards_json_positions_field_is_consistently_a_list(mock_config_cls, mock_db_cls):
    """JSON payload should always return positions as a list."""
    mock_config = Mock()
    mock_config.get.return_value = None
    mock_config_cls.return_value = mock_config

    mock_db = Mock()
    mock_db.get_positions.return_value = [
        {
            "title": "Will BTC hit 100k?",
            "entry_price": 0.55,
            "shares": 100.0,
            "entry_date": "2026-02-25T00:00:00",
            "side": "YES",
        }
    ]
    mock_db_cls.return_value = mock_db

    runner = CliRunner()
    result = runner.invoke(cli, ["rewards", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert isinstance(payload["positions"], list)
    assert len(payload["positions"]) == 1
    assert payload["positions_count"] == 1
