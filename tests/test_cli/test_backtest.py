"""CLI tests for backtest demo quarantine."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli


@patch("polyterm.cli.main.Config")
def test_backtest_without_demo_refuses_to_invent_history(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["backtest", "--format", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["uses_historical_data"] is False
    assert payload["mode"] == "unavailable"
    assert "does not replay historical" in payload["error"]
    assert "results" not in payload


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.backtest.GammaClient")
def test_backtest_demo_json_is_labeled_simulation(mock_gamma_cls, mock_config_cls):
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = ""
    mock_config_cls.return_value = mock_config

    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = []
    mock_gamma.get_markets.return_value = [{"question": "Demo market", "tokens": []}]
    mock_gamma_cls.return_value = mock_gamma

    result = CliRunner().invoke(cli, ["backtest", "--demo", "--format", "json", "-p", "7d"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["uses_historical_data"] is False
    assert payload["mode"] == "demo_random_simulation"
    assert "does not replay historical" in payload["disclosure"]
    assert payload["results"]["uses_historical_data"] is False
