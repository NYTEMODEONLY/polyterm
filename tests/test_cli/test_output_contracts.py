"""CLI output contract tests for JSON mode."""

import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli
from polyterm.utils.json_output import AGENT_SCHEMA_VERSION


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


@patch("polyterm.cli.commands.wallets.Database")
def test_wallets_smart_json_accepts_agent_threshold_options(mock_db_cls, tmp_path, monkeypatch):
    """`wallets --type smart --format json` should expose smart-money thresholds."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_db = Mock()
    mock_db.get_smart_money_wallets.return_value = []
    mock_db_cls.return_value = mock_db

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["wallets", "--type", "smart", "--min-win-rate", "0.8", "--min-trades", "12", "--limit", "5", "--format", "json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["type"] == "smart"
    mock_db.get_smart_money_wallets.assert_called_once_with(min_win_rate=0.8, min_trades=12)


@patch("polyterm.cli.commands.compare.MarketComparisonEngine")
def test_compare_json_output_uses_stable_envelope_without_preamble(mock_engine_cls, tmp_path, monkeypatch):
    """`compare --format json` should be pure agent-envelope JSON."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_engine = Mock()
    mock_engine.compare.return_value = {"query": ["a", "b"], "count": 2, "pairwise": []}
    mock_engine_cls.return_value = mock_engine

    runner = CliRunner()
    result = runner.invoke(cli, ["compare", "-m", "a", "-m", "b", "--format", "json"])

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == AGENT_SCHEMA_VERSION
    assert payload["success"] is True
    assert payload["data"] == {"query": ["a", "b"], "count": 2, "pairwise": []}
    assert payload["meta"]["tool"] == "market.compare"
    mock_engine.compare.assert_called_once_with(["a", "b"], hours=24)


@patch("polyterm.cli.commands.scan_opportunities.MarketOpportunityScanner")
def test_scan_opportunities_json_output_uses_stable_envelope(mock_scanner_cls, tmp_path, monkeypatch):
    """`scan-opportunities --format json` should be pure agent-envelope JSON."""
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_scanner = Mock()
    mock_scanner.scan.return_value = {"query": "bitcoin", "opportunities": [{"market_id": "m1"}]}
    mock_scanner_cls.return_value = mock_scanner

    runner = CliRunner()
    result = runner.invoke(
        cli,
        [
            "scan-opportunities",
            "--query",
            "bitcoin",
            "--limit",
            "3",
            "--min-volume",
            "5000",
            "--min-liquidity",
            "1000",
            "--max-archive-age-hours",
            "12",
            "--format",
            "json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["schema_version"] == AGENT_SCHEMA_VERSION
    assert payload["success"] is True
    assert payload["data"] == {"query": "bitcoin", "opportunities": [{"market_id": "m1"}]}
    assert payload["meta"]["tool"] == "scan.opportunities"
    mock_scanner.scan.assert_called_once_with(
        query="bitcoin",
        limit=3,
        min_volume=5000.0,
        min_liquidity=1000.0,
        max_archive_age_hours=12,
    )
