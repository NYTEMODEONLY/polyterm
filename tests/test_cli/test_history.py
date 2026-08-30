"""CLI tests for history: CLOB path, refuse, and labeled demo."""

import inspect
import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli
from polyterm.core.price_history import DEMO_DISCLOSURE
from polyterm.tui.screens.history_screen import run_history_screen


def _config_mock():
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = ""
    mock_config.clob_rest_endpoint = "https://clob.example.com"
    return mock_config


def _market_payload(**overrides):
    market = {
        "id": "market-1",
        "question": "Will BTC hit 100k?",
        "outcomePrices": ["0.55"],
        "clobTokenIds": ["token-yes", "token-no"],
        "volume24hr": 1000,
        "volume": 50000,
    }
    market.update(overrides)
    return market


@patch("polyterm.cli.main.Config")
def test_history_help_describes_clob_and_demo(mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    result = CliRunner().invoke(cli, ["history", "--help"])
    assert result.exit_code == 0
    assert "CLOB" in result.output
    assert "--demo" in result.output
    assert "refuses" in result.output.lower() or "random walk" in result.output.lower()


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.history.CLOBClient")
@patch("polyterm.cli.commands.history.GammaClient")
def test_history_json_uses_clob_prices_history(mock_gamma_cls, mock_clob_cls, mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = [_market_payload()]
    mock_gamma_cls.return_value = mock_gamma

    mock_clob = Mock()
    mock_clob.get_price_history.return_value = [
        {"t": 1_700_000_000, "p": "0.40"},
        {"t": 1_700_086_400, "p": "0.55"},
    ]
    mock_clob_cls.return_value = mock_clob

    with patch("polyterm.cli.commands.history.build_time_bounds", return_value=(1_700_000_000, 1_700_086_400)):
        result = CliRunner().invoke(cli, ["history", "bitcoin", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["uses_historical_data"] is True
    assert payload["source"] == "clob_prices_history"
    assert payload["clob_token_id"] == "token-yes"
    assert payload["history"]["points"][0]["price"] == 0.40
    assert payload["history"]["points"][-1]["price"] == 0.55
    kwargs = mock_clob.get_price_history.call_args.kwargs
    assert kwargs["interval"] == "max"
    assert kwargs["fidelity"] == 3600
    mock_clob.close.assert_called_once()
    mock_gamma.close.assert_called_once()


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.history.CLOBClient")
@patch("polyterm.cli.commands.history.GammaClient")
def test_history_refuses_without_clob_token_ids(mock_gamma_cls, mock_clob_cls, mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = [_market_payload(clobTokenIds=[])]
    mock_gamma_cls.return_value = mock_gamma

    result = CliRunner().invoke(cli, ["history", "bitcoin", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["uses_historical_data"] is False
    assert payload["source"] == "none"
    assert "history" not in payload
    mock_clob_cls.assert_not_called()


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.history.CLOBClient")
@patch("polyterm.cli.commands.history.GammaClient")
def test_history_refuses_when_clob_returns_empty(mock_gamma_cls, mock_clob_cls, mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = [_market_payload()]
    mock_gamma_cls.return_value = mock_gamma
    mock_clob = Mock()
    mock_clob.get_price_history.return_value = []
    mock_clob_cls.return_value = mock_clob

    result = CliRunner().invoke(cli, ["history", "bitcoin", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["uses_historical_data"] is False
    assert payload["source"] == "none"
    assert "does not invent" in payload["error"]
    mock_clob.close.assert_called_once()


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.history.CLOBClient")
@patch("polyterm.cli.commands.history.GammaClient")
def test_history_refuses_when_clob_raises(mock_gamma_cls, mock_clob_cls, mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = [_market_payload()]
    mock_gamma_cls.return_value = mock_gamma
    mock_clob = Mock()
    mock_clob.get_price_history.side_effect = Exception("history failed")
    mock_clob_cls.return_value = mock_clob

    result = CliRunner().invoke(cli, ["history", "bitcoin", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["uses_historical_data"] is False
    mock_clob.close.assert_called_once()


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.history.CLOBClient")
@patch("polyterm.cli.commands.history.GammaClient")
def test_history_demo_json_is_labeled_synthetic(mock_gamma_cls, mock_clob_cls, mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = [_market_payload()]
    mock_gamma_cls.return_value = mock_gamma

    result = CliRunner().invoke(cli, ["history", "bitcoin", "--demo", "--format", "json"])

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["uses_historical_data"] is False
    assert payload["source"] == "demo_random_walk"
    assert "does not invent" not in payload.get("error", "")
    assert DEMO_DISCLOSURE in payload["disclosure"]
    assert payload["history"]["points"]
    mock_clob_cls.assert_not_called()


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.history.GammaClient")
def test_history_demo_table_discloses_before_series(mock_gamma_cls, mock_config_cls):
    mock_config_cls.return_value = _config_mock()
    mock_gamma = Mock()
    mock_gamma.search_markets.return_value = [_market_payload()]
    mock_gamma_cls.return_value = mock_gamma

    result = CliRunner().invoke(cli, ["history", "bitcoin", "--demo"])

    assert result.exit_code == 0, result.output
    disclosure_at = result.output.find("DEMO SERIES")
    series_at = result.output.find("DEMO Price Path")
    assert disclosure_at != -1
    assert series_at != -1
    assert disclosure_at < series_at
    assert "uses_historical_data" in result.output
    assert "demo_random_walk" in result.output


def test_history_screen_does_not_auto_enable_demo():
    source = inspect.getsource(run_history_screen)
    assert "--demo" not in source
    assert "prices-history" in source
    assert "polyterm.cli.main" in source
    assert "history" in source


def test_history_cli_default_path_does_not_import_random():
    from polyterm.cli.commands import history as history_cmd

    source = inspect.getsource(history_cmd)
    assert "import random" not in source
    assert "_generate_history_points" not in source
