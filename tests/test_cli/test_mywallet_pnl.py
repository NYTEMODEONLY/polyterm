"""CLI tests for `polyterm mywallet --pnl`. No live network."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.api.data_api_lag import DISCLOSURE, QUALITY_FLAG
from polyterm.cli.main import cli


WALLET = "0x0000000000000000000000000000000000000001"


def _report(**overrides):
    payload = {
        "address": WALLET,
        "source": "activity-cashflow",
        "vs_leaderboard": "pre-fee",
        "vs-leaderboard": "pre-fee",
        "lag": True,
        "lagged": True,
        "pnl": 11600.0,
        "cashflow": 11400.0,
        "open_mark": 200.0,
        "open_positions": 1,
        "leaderboard_profit": 11800.0,
        "activity_count": 3,
        "included_counts": {"buy": 1, "sell": 1, "redeem": 1, "merge": 0, "split": 0, "rebate": 0},
        "totals": {"buy": 1000.0, "sell": 400.0, "redeem": 12000.0, "merge": 0.0, "split": 0.0, "rebate": 0.0},
        "skipped_unknown": 0,
        "skipped_malformed": 0,
        "unknown_types": [],
        "empty": False,
        "quality_flags": [QUALITY_FLAG],
    }
    payload.update(overrides)
    return payload


@patch("polyterm.cli.main.Config")
def test_mywallet_help_shows_pnl_and_lag(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["mywallet", "--help"])
    assert result.exit_code == 0, result.output
    assert "--pnl" in result.output
    output = result.output.lower()
    assert "cashflow" in output or "activity" in output
    assert "lagged" in output
    assert "clob" in output
    assert "live_data_api_trades" not in output


@patch("polyterm.cli.main.Config")
@patch("polyterm.core.pnl_cashflow.CashflowPnl")
@patch("polyterm.api.data_api.DataAPIClient")
@patch("polyterm.cli.commands.mywallet.Database")
@patch("polyterm.cli.commands.mywallet.GammaClient")
@patch("polyterm.cli.commands.mywallet.CLOBClient")
def test_mywallet_pnl_json_is_parseable_and_labeled(
    mock_clob, mock_gamma, mock_db, mock_data_api, mock_pnl_cls, mock_config_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_config_cls.return_value = Mock()
    mock_config_cls.return_value.get.return_value = None
    mock_pnl_cls.return_value.compute.return_value = _report()

    result = CliRunner().invoke(
        cli,
        ["mywallet", "--pnl", "--address", WALLET, "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["wallet"] == WALLET
    assert payload["source"] == "activity-cashflow"
    assert payload["vs_leaderboard"] == "pre-fee"
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert "lag_seconds" not in payload
    cashpnl_sum = -3500.0
    assert payload["pnl"] != cashpnl_sum
    assert payload["pnl"] == 11600.0
    assert "cashPnl" not in payload
    mock_pnl_cls.return_value.compute.assert_called_once_with(WALLET)


@patch("polyterm.cli.main.Config")
@patch("polyterm.core.pnl_cashflow.CashflowPnl")
@patch("polyterm.api.data_api.DataAPIClient")
@patch("polyterm.cli.commands.mywallet.Database")
@patch("polyterm.cli.commands.mywallet.GammaClient")
@patch("polyterm.cli.commands.mywallet.CLOBClient")
def test_mywallet_pnl_empty_json_is_honest(
    mock_clob, mock_gamma, mock_db, mock_data_api, mock_pnl_cls, mock_config_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_config_cls.return_value = Mock()
    mock_config_cls.return_value.get.return_value = None
    mock_pnl_cls.return_value.compute.return_value = _report(
        pnl=None,
        cashflow=None,
        open_mark=0.0,
        open_positions=0,
        leaderboard_profit=None,
        activity_count=0,
        empty=True,
        quality_flags=[QUALITY_FLAG, "empty_activity"],
    )

    result = CliRunner().invoke(
        cli,
        ["mywallet", "--pnl", "--address", WALLET, "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["empty"] is True
    assert payload["pnl"] is None
    assert payload["source"] == "activity-cashflow"
    assert payload["vs_leaderboard"] == "pre-fee"


@patch("polyterm.cli.main.Config")
@patch("polyterm.core.pnl_cashflow.CashflowPnl")
@patch("polyterm.api.data_api.DataAPIClient")
@patch("polyterm.cli.commands.mywallet.Database")
@patch("polyterm.cli.commands.mywallet.GammaClient")
@patch("polyterm.cli.commands.mywallet.CLOBClient")
def test_mywallet_pnl_error_json_reports_failure(
    mock_clob, mock_gamma, mock_db, mock_data_api, mock_pnl_cls, mock_config_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_config_cls.return_value = Mock()
    mock_config_cls.return_value.get.return_value = None
    mock_pnl_cls.return_value.compute.side_effect = ConnectionError("Data API down")

    result = CliRunner().invoke(
        cli,
        ["mywallet", "--pnl", "--address", WALLET, "--format", "json"],
    )
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert "Data API down" in payload["error"]


@patch("polyterm.cli.main.Config")
@patch("polyterm.core.pnl_cashflow.CashflowPnl")
@patch("polyterm.api.data_api.DataAPIClient")
@patch("polyterm.cli.commands.mywallet.Database")
@patch("polyterm.cli.commands.mywallet.GammaClient")
@patch("polyterm.cli.commands.mywallet.CLOBClient")
def test_mywallet_pnl_table_banners_lag(
    mock_clob, mock_gamma, mock_db, mock_data_api, mock_pnl_cls, mock_config_cls, tmp_path, monkeypatch
):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_config_cls.return_value = Mock()
    mock_config_cls.return_value.get.return_value = None
    mock_pnl_cls.return_value.compute.return_value = _report()

    result = CliRunner().invoke(cli, ["mywallet", "--pnl", "--address", WALLET])
    assert result.exit_code == 0, result.output
    assert "activity-cashflow" in result.output
    assert "pre-fee" in result.output
    assert "Lagged Data API" in result.output or DISCLOSURE.split("(")[0].strip() in result.output
    assert "not live CLOB" in result.output
    assert "live_data_api_trades" not in result.output


@patch("polyterm.cli.main.Config")
def test_mywallet_pnl_json_without_address_does_not_prompt(mock_config_cls, tmp_path, monkeypatch):
    monkeypatch.setattr("pathlib.Path.home", lambda: tmp_path)
    mock_config = Mock()
    mock_config.get.return_value = None
    mock_config_cls.return_value = mock_config

    result = CliRunner().invoke(cli, ["mywallet", "--pnl", "--format", "json"])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert payload["error"] == "No wallet connected"
