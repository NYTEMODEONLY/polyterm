"""CLI output contract tests for JSON mode."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli


@patch("polyterm.cli.commands.whales.AnalyticsEngine")
@patch("polyterm.cli.commands.whales.CLOBClient")
@patch("polyterm.cli.commands.whales.GammaClient")
def test_whales_json_output_is_valid_json(mock_gamma_cls, mock_clob_cls, mock_analytics_cls, tmp_path, monkeypatch):
    """`whales --format json` should emit pure JSON with no preamble text."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    mock_gamma = Mock()
    mock_clob = Mock()
    mock_gamma_cls.return_value = mock_gamma
    mock_clob_cls.return_value = mock_clob

    trade = SimpleNamespace(
        market_id="market-1",
        data={"_market_title": "Market 1"},
        outcome="YES",
        price=0.61,
        notional=125000.0,
        timestamp=1700000000,
    )
    mock_analytics = Mock()
    mock_analytics.track_whale_trades.return_value = [trade]
    mock_analytics_cls.return_value = mock_analytics

    runner = CliRunner()
    result = runner.invoke(cli, ["whales", "--format", "json", "--limit", "1"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["trades"][0]["market_id"] == "market-1"


def test_mywallet_positions_without_connected_wallet_returns_json_error(tmp_path, monkeypatch):
    """`mywallet --positions --format json` should return machine-readable errors."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)

    runner = CliRunner()
    result = runner.invoke(cli, ["mywallet", "--positions", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["error"] == "No wallet connected"


def test_mywallet_positions_json_output_is_valid_json(tmp_path, monkeypatch):
    """`mywallet --positions --format json` should be pure JSON when wallet is provided."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    wallet = "0x" + "1" * 40

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["mywallet", "--address", wallet, "--positions", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["wallet"] == wallet
    assert payload["positions"] == []
