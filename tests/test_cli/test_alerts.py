"""CLI tests for print alert rules. No live network."""

import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from polyterm.api.data_api_lag import DISCLOSURE, QUALITY_FLAG
from polyterm.cli.main import cli
from polyterm.core.print_scanner import PrintScanner
from polyterm.db.database import Database
from polyterm.db.models import Alert


def _config_mock():
    mock_config = Mock()
    mock_config.notification_config = {
        "telegram": {"enabled": False},
        "discord": {"enabled": False},
        "system": {"enabled": False},
    }
    return mock_config


@patch("polyterm.cli.main.Config")
def test_alerts_help_shows_print_rule(mock_config_cls):
    mock_config_cls.return_value = Mock()
    result = CliRunner().invoke(cli, ["alerts", "--help"])
    assert result.exit_code == 0, result.output
    output = result.output.lower()
    assert "--add-rule" in result.output
    assert "print" in output
    assert "lagged" in output
    assert "data api" in output
    assert "clob" in output
    assert "--evaluate" in result.output
    assert "--min-notional" in result.output


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.Database")
def test_add_print_rule_dry_run_json_does_not_write(mock_db_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    db = Database(str(tmp_path / "alerts.db"))
    mock_db_cls.return_value = db

    result = CliRunner().invoke(cli, [
        "alerts",
        "--add-rule", "print",
        "--min-notional", "10000",
        "--market", "bitcoin-100k",
        "--dry-run",
        "--format", "json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["created"] is False
    assert payload["dry_run"] is True
    assert payload["rule"]["rule_type"] == "print"
    assert payload["rule"]["min_notional"] == 10000.0
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert payload["source"] == "data_api"
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert db.get_alert_rules() == []
    assert db.get_recent_alerts() == []


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.Database")
def test_add_print_rule_without_min_notional_errors_json(mock_db_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    mock_db_cls.return_value = Database(str(tmp_path / "alerts.db"))
    result = CliRunner().invoke(cli, [
        "alerts", "--add-rule", "print", "--format", "json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert "--min-notional" in payload["error"]


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.AlertEngine")
@patch("polyterm.cli.commands.alerts.Database")
def test_evaluate_print_json_is_lagged(mock_db_cls, mock_engine_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    db = Database(str(tmp_path / "alerts.db"))
    mock_db_cls.return_value = db
    engine = Mock()
    engine.run_print_once.return_value = {
        "rule_type": "print",
        "min_notional": 10000,
        "triggered": True,
        "fetched": 1,
        "skipped": 0,
        "matched": 1,
        "dry_run": True,
        "prints": [{
            "wallet": "0xabc",
            "notional": 12000,
            "source": "data_api",
            "lag": True,
            "lagged": True,
        }],
        "alerts": [],
        "source": "data_api",
        "lag": True,
        "lagged": True,
        "quality_flags": [QUALITY_FLAG, "public_trade_rows_only", "single_scan"],
    }
    mock_engine_cls.return_value = engine

    result = CliRunner().invoke(cli, [
        "alerts",
        "--evaluate", "print",
        "--min-notional", "10000",
        "--dry-run",
        "--format", "json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["lagged"] is True
    assert payload["lag"] is True
    assert payload["source"] == "data_api"
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in json.dumps(payload)
    engine.run_print_once.assert_called_once()
    assert engine.run_print_once.call_args[1]["dry_run"] is True


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.Database")
def test_evaluate_print_empty_json_is_not_invented_tape(mock_db_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    db = Database(str(tmp_path / "alerts.db"))
    mock_db_cls.return_value = db

    class EmptyAPI:
        def get_recent_trades(self, **kwargs):
            return []

        def get_trades(self, **kwargs):
            return []

    with patch("polyterm.core.alert_engine.PrintScanner", return_value=PrintScanner(data_api=EmptyAPI())):
        result = CliRunner().invoke(cli, [
            "alerts",
            "--evaluate", "print",
            "--min-notional", "10000",
            "--dry-run",
            "--format", "json",
        ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["triggered"] is False
    assert payload["prints"] == []
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert db.get_recent_alerts() == []


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.Database")
def test_evaluate_print_error_json(mock_db_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    mock_db_cls.return_value = Database(str(tmp_path / "alerts.db"))

    class BoomAPI:
        def get_recent_trades(self, **kwargs):
            raise ConnectionError("data api down")

        def get_trades(self, **kwargs):
            raise ConnectionError("data api down")

    with patch("polyterm.core.alert_engine.PrintScanner", return_value=PrintScanner(data_api=BoomAPI())):
        result = CliRunner().invoke(cli, [
            "alerts",
            "--evaluate", "print",
            "--min-notional", "10000",
            "--format", "json",
        ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is False
    assert "data api down" in payload["error"]


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.Database")
def test_list_print_alerts_json_includes_lag_flags(mock_db_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    db = Database(str(tmp_path / "alerts.db"))
    db.insert_alert(Alert(
        alert_type="print",
        market_id="bitcoin-100k",
        wallet_address="0xabc",
        severity=50,
        message="Lagged Data API print $12000 BUY on bitcoin-100k",
        data={"print": {"lagged": True, "source": "data_api"}},
    ))
    mock_db_cls.return_value = db

    result = CliRunner().invoke(cli, [
        "alerts", "--type", "print", "--format", "json",
    ])
    assert result.exit_code == 0, result.output
    payload = json.loads(result.output)
    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert payload["alerts"][0]["alert_type"] == "print"


@patch("polyterm.cli.main.Config")
@patch("polyterm.cli.commands.alerts.Database")
def test_list_print_alerts_table_banners_lag(mock_db_cls, mock_config_cls, tmp_path):
    mock_config_cls.return_value = _config_mock()
    db = Database(str(tmp_path / "alerts.db"))
    db.insert_alert(Alert(
        alert_type="print",
        market_id="bitcoin-100k",
        severity=50,
        message="Lagged Data API print $12000",
        data={},
    ))
    mock_db_cls.return_value = db

    result = CliRunner().invoke(cli, ["alerts", "--type", "print"])
    assert result.exit_code == 0, result.output
    assert "Lagged Data API" in result.output
    assert "not live CLOB" in result.output
    assert DISCLOSURE.split("(")[0].strip() in result.output or "lagged Data API" in result.output
