"""CLI tests for leaderboard honesty."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli
from polyterm.core.leaderboard import WINRATE_UNSUPPORTED_MESSAGE


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.leaderboard.DataAPIClient")
def test_leaderboard_json_uses_real_rows_and_omits_fake_win_rate(mock_client_cls, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_client = Mock()
    mock_client.get_leaderboard.return_value = [
        {
            "rank": "1",
            "proxyWallet": "0x983eedfbd75803602e4a6e6ea9aab6dc6b9c6748",
            "userName": "3edmond.dantes",
            "vol": 1000,
            "pnl": 250,
        }
    ]
    mock_client_cls.return_value = mock_client

    result = CliRunner().invoke(cli, ["leaderboard", "--format", "json", "-l", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["source"] == "data-api"
    assert payload["endpoint"] == "/v1/leaderboard"
    assert payload["traders"][0]["address"].startswith("0x983eed")
    assert payload["traders"][0]["volume"] == 1000
    assert payload["traders"][0]["profit"] == 250
    assert payload["traders"][0]["win_rate"] is None
    assert "win_rate_not_provided" in payload["quality_flags"]
    mock_client.get_leaderboard.assert_called_once()
    assert mock_client.get_leaderboard.call_args.kwargs["sort_by"] == "profit"


@patch("polyterm.cli.main.Config")
def test_leaderboard_winrate_on_data_api_is_refused(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["leaderboard", "-t", "winrate", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["error"] == WINRATE_UNSUPPORTED_MESSAGE
    assert "winrate_unsupported_by_public_leaderboard" in payload["quality_flags"]


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.leaderboard.DataAPIClient")
def test_leaderboard_does_not_invent_rows_on_empty_response(mock_client_cls, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_client = Mock()
    mock_client.get_leaderboard.return_value = []
    mock_client_cls.return_value = mock_client

    result = CliRunner().invoke(cli, ["leaderboard", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["traders"] == []
