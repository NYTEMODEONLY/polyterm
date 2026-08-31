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
@patch("polyterm.cli.commands.whales.WalletIntelligence")
@patch("polyterm.cli.commands.whales.Database")
def test_whales_wallets_json_uses_wallet_mode(mock_db_cls, mock_intel_cls, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_db_cls.return_value = Mock()
    mock_intel = Mock()
    mock_intel.live_whales.return_value = {
        "wallets": [{"address": "0xabc", "trade_count": 2, "notional": 200000, "largest_trade": 150000, "top_markets": []}],
        "quality_flags": ["lagged_data_api"],
        "lag": True,
        "lagged": True,
        "source": "public_data_api",
    }
    mock_intel_cls.return_value = mock_intel

    result = CliRunner().invoke(cli, ["whales", "--wallets", "--format", "json", "--limit", "1"])
    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["mode"] == "wallet_trades"
    assert payload["wallets"][0]["address"] == "0xabc"
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert "lagged_data_api" in payload["quality_flags"]
