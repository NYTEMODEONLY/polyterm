"""CLI tests for whale vs volume-heuristic honesty."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.cli.main import cli
from polyterm.core.volume_spikes import HighVolumeMarket


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.detect_high_volume_markets")
@patch("polyterm.cli.commands.whales.GammaClient")
def test_whales_default_json_is_volume_heuristic_without_trader(mock_gamma_cls, mock_detect, mock_config_cls):
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = ""
    mock_config_cls.return_value = mock_config
    mock_gamma_cls.return_value = Mock()
    mock_detect.return_value = [
        HighVolumeMarket(
            market_id="market-1",
            market_title="Market 1",
            volume_24hr=125000.0,
            last_price=0.61,
            outcome_lean="YES",
            timestamp=1700000000,
        )
    ]

    result = CliRunner().invoke(cli, ["whales", "--format", "json", "--limit", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["mode"] == "volume_heuristic"
    assert payload["evidence_level"] == "gamma_volume24hr_heuristic"
    assert "trades" not in payload
    assert payload["markets"][0]["market_id"] == "market-1"
    assert "trader" not in payload["markets"][0]


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.scan_whale_prints")
def test_whales_wallets_json_uses_wallet_mode(mock_scan, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_scan.return_value = {
        "wallets": [{"address": "0xabc", "trade_count": 2, "notional": 200000, "largest_trade": 150000, "top_markets": []}],
        "prints": [{"wallet": "0xabc", "notional": 200000, "source": "data_api", "lag": True, "lagged": True}],
        "quality_flags": ["lagged_data_api"],
        "lag": True,
        "lagged": True,
        "source": "data_api",
    }

    result = CliRunner().invoke(cli, ["whales", "--wallets", "--format", "json", "--limit", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["mode"] == "wallet_trades"
    assert payload["wallets"][0]["address"] == "0xabc"
    assert payload["prints"][0]["wallet"] == "0xabc"
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert payload["source"] == "data_api"
    assert "lagged_data_api" in payload["quality_flags"]
    assert "insider_score" not in payload
    assert "live_data_api_trades" not in payload["quality_flags"]
    mock_scan.assert_called_once()
    assert mock_scan.call_args.kwargs["min_notional"] == 10000.0


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.scan_whale_prints")
def test_whales_wallets_json_empty_tape_is_empty(mock_scan, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_scan.return_value = {
        "wallets": [],
        "prints": [],
        "count": 0,
        "wallet_count": 0,
        "quality_flags": ["lagged_data_api", "empty_data_api_page"],
        "source": "data_api",
        "lag": True,
        "lagged": True,
    }

    result = CliRunner().invoke(cli, ["whales", "--wallets", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["prints"] == []
    assert payload["wallets"] == []
    assert "insider_score" not in payload


@patch("polyterm.cli.main.Config")
def test_whales_wallets_help_mentions_lagged_prints_and_min_notional(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["whales", "--wallets", "--help"])
    assert result.exit_code == 0, result.output
    output = result.output.lower()
    assert "lagged" in output
    assert "data api" in output
    assert "not live clob" in output
    assert "--min-notional" in result.output
    assert "insider_score" not in output
    assert "80%" not in output


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.scan_whale_prints")
def test_whales_wallets_accepts_min_notional(mock_scan, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_scan.return_value = {
        "wallets": [],
        "prints": [],
        "quality_flags": ["lagged_data_api"],
        "source": "data_api",
        "lag": True,
        "lagged": True,
    }
    result = CliRunner().invoke(
        cli,
        ["whales", "--wallets", "--min-notional", "25000", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    assert mock_scan.call_args.kwargs["min_notional"] == 25000.0
    payload = json.loads(result.output)
    assert payload["lagged"] is True
