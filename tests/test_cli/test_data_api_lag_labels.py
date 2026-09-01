"""CLI/TUI labels for lagged Data API wallet, positions, and trades. No live network."""

import inspect
import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.api.data_api_lag import DISCLOSURE, QUALITY_FLAG
from polyterm.cli.main import cli
from polyterm.tui.screens.portfolio import portfolio_screen
from polyterm.tui.screens.wallets import wallets_screen
from polyterm.tui.screens.whales import whales_screen


def _wallet_profile():
    return {
        "address": "0xabc",
        "metrics": {
            "position_count": 1,
            "trade_count": 2,
            "total_volume": 1000,
            "win_rate": 0.5,
        },
        "tags": ["whale"],
        "quality_flags": ["trade_direction_may_be_inferred"],
        "source": {"positions": "data-api", "trades": "data-api", "local_wallet": False},
    }


@patch("polyterm.cli.main.Config")
def test_wallets_help_mentions_lagged_data_api(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["wallets", "--help"])
    assert result.exit_code == 0
    output = result.output.lower()
    assert "lagged" in output
    assert "clob" in output
    assert "--refresh" in result.output


@patch("polyterm.cli.main.Config")
def test_whales_help_mentions_lagged_data_api(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["whales", "--help"])
    assert result.exit_code == 0
    output = result.output.lower()
    assert "lagged" in output
    assert "clob" in output
    assert "--wallets" in result.output


@patch("polyterm.cli.main.Config")
def test_portfolio_help_mentions_lagged_data_api(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["portfolio", "--help"])
    assert result.exit_code == 0
    output = result.output.lower()
    assert "lagged" in output
    assert "clob" in output


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.wallets.WalletIntelligence")
@patch("polyterm.cli.commands.wallets.DataAPIClient")
@patch("polyterm.cli.commands.wallets.Database")
def test_wallets_refresh_json_is_lagged(mock_db_cls, mock_data_api_cls, mock_intel_cls, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_db_cls.return_value = Mock()
    mock_data_api_cls.return_value = Mock()
    mock_intel = Mock()
    mock_intel.analyze_wallet.return_value = _wallet_profile()
    mock_intel_cls.return_value = mock_intel

    result = CliRunner().invoke(
        cli,
        ["wallets", "--analyze", "0xabc", "--refresh", "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    profile = payload["wallet_intelligence"]
    assert profile["lag"] is True
    assert profile["lagged"] is True
    assert QUALITY_FLAG in profile["quality_flags"]
    assert "live_data_api_trades" not in profile["quality_flags"]


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.wallets.WalletIntelligence")
@patch("polyterm.cli.commands.wallets.DataAPIClient")
@patch("polyterm.cli.commands.wallets.Database")
def test_wallets_refresh_table_banners_lag(mock_db_cls, mock_data_api_cls, mock_intel_cls, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_db_cls.return_value = Mock()
    mock_data_api_cls.return_value = Mock()
    mock_intel = Mock()
    mock_intel.analyze_wallet.return_value = _wallet_profile()
    mock_intel_cls.return_value = mock_intel

    result = CliRunner().invoke(cli, ["wallets", "--analyze", "0xabc", "--refresh"])
    assert result.exit_code == 0, result.output
    assert DISCLOSURE.split("(")[0].strip() in result.output or "Lagged Data API" in result.output
    assert "not live CLOB" in result.output


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.scan_whale_prints")
def test_whales_wallets_json_is_lagged(mock_scan, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_scan.return_value = {
        "wallets": [
            {
                "address": "0xabc",
                "trade_count": 2,
                "notional": 200000,
                "largest_trade": 150000,
                "top_markets": [],
            }
        ],
        "prints": [
            {
                "wallet": "0xabc",
                "notional": 200000,
                "side": "BUY",
                "source": "data_api",
                "lag": True,
                "lagged": True,
            }
        ],
        "quality_flags": ["public_trade_rows_only"],
        "source": "data_api",
    }

    result = CliRunner().invoke(cli, ["whales", "--wallets", "--format", "json", "--limit", "1"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert payload["source"] == "data_api"
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert "insider_score" not in payload


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.scan_whale_prints")
def test_whales_wallets_table_banners_lag(mock_scan, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_scan.return_value = {
        "wallets": [
            {
                "address": "0xabc",
                "trade_count": 2,
                "notional": 200000,
                "largest_trade": 150000,
                "top_markets": [("slug", 1)],
            }
        ],
        "prints": [
            {
                "wallet": "0xabc",
                "notional": 200000,
                "side": "BUY",
                "market_slug": "slug",
                "timestamp_iso": "2023-11-14T22:13:20+00:00",
            }
        ],
        "wallet_count": 1,
        "quality_flags": ["public_trade_rows_only"],
    }

    result = CliRunner().invoke(cli, ["whales", "--wallets", "--limit", "1"])
    assert result.exit_code == 0, result.output
    assert "Lagged Data API" in result.output
    assert "not live CLOB" in result.output
    assert "0xabc" in result.output


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.whales.WalletIntelligence")
@patch("polyterm.cli.commands.whales.Database")
def test_whales_local_json_is_not_labeled_data_api_lag(mock_db_cls, mock_intel_cls, mock_config_cls):
    mock_config_cls.return_value = Mock()
    mock_db_cls.return_value = Mock()
    mock_intel = Mock()
    mock_intel.local_whales.return_value = {
        "wallets": [],
        "quality_flags": ["local_db_only"],
    }
    mock_intel_cls.return_value = mock_intel

    result = CliRunner().invoke(cli, ["whales", "--wallets", "--local", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload.get("lagged") is not True
    assert QUALITY_FLAG not in payload.get("quality_flags", [])


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.portfolio.AnalyticsEngine")
@patch("polyterm.cli.commands.portfolio.CLOBClient")
@patch("polyterm.cli.commands.portfolio.GammaClient")
def test_portfolio_table_banners_lag(mock_gamma_cls, mock_clob_cls, mock_analytics_cls, mock_config_cls):
    mock_config = Mock()
    mock_config.gamma_base_url = "https://gamma.example.com"
    mock_config.gamma_api_key = ""
    mock_config.clob_rest_endpoint = "https://clob.example.com"
    mock_config.clob_endpoint = "wss://ws.example.com"
    mock_config.wallet_address = None
    mock_config_cls.return_value = mock_config
    mock_gamma_cls.return_value = Mock()
    mock_clob_cls.return_value = Mock()
    mock_analytics = Mock()
    mock_analytics.get_portfolio_analytics.return_value = {
        "wallet_address": "0xabc",
        "total_positions": 1,
        "total_value": 10.0,
        "total_pnl": 1.0,
        "roi_percent": 10.0,
        "data_source": "data_api",
        "positions": [
            {
                "market": "m1",
                "title": "Market 1",
                "outcome": "YES",
                "size": 1,
                "averagePrice": 0.5,
                "currentValue": 10,
                "pnl": 1,
            }
        ],
    }
    mock_analytics_cls.return_value = mock_analytics

    result = CliRunner().invoke(cli, ["portfolio", "--wallet", "0xabc"])
    assert result.exit_code == 0, result.output
    assert "Lagged Data API" in result.output
    assert "not live CLOB" in result.output


def test_tui_screens_disclose_lagged_data_api():
    wallets_src = inspect.getsource(wallets_screen)
    whales_src = inspect.getsource(whales_screen)
    portfolio_src = inspect.getsource(portfolio_screen)
    assert "lagged" in wallets_src.lower()
    assert "not live CLOB" in wallets_src
    assert "lagged Data API" in whales_src
    assert "not live CLOB" in whales_src
    assert "lagged Data API" in portfolio_src
    assert "not live CLOB" in portfolio_src
