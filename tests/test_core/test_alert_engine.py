"""Tests for AlertEngine print rules. No live network."""

import pytest

from polyterm.api.data_api_lag import QUALITY_FLAG, SOURCE
from polyterm.core.alert_engine import AlertEngine
from polyterm.core.print_scanner import PrintScanner
from polyterm.db.database import Database


class _FakeDataAPI:
    def __init__(self, payload):
        self.payload = payload

    def get_recent_trades(self, **kwargs):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def get_trades(self, **kwargs):
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def _engine(tmp_path, payload):
    db = Database(str(tmp_path / "alerts.db"))
    scanner = PrintScanner(data_api=_FakeDataAPI(payload))
    return db, AlertEngine(database=db, print_scanner=scanner)


def test_create_print_rule_dry_run_does_not_write(tmp_path):
    db, engine = _engine(tmp_path, [])
    result = engine.create_print_rule(min_notional=10000, market="bitcoin-100k", dry_run=True)
    assert result["created"] is False
    assert result["dry_run"] is True
    assert result["rule"]["rule_type"] == "print"
    assert result["rule"]["min_notional"] == 10000
    assert result["source"] == SOURCE
    assert result["lag"] is True
    assert result["lagged"] is True
    assert QUALITY_FLAG in result["quality_flags"]
    assert "live_data_api_trades" not in result["quality_flags"]
    assert db.get_alert_rules() == []
    assert db.get_recent_alerts() == []


def test_create_print_rule_writes_alert_rules_table(tmp_path):
    db, engine = _engine(tmp_path, [])
    result = engine.create_print_rule(
        min_notional=25000,
        wallet="0xabc",
        dry_run=False,
    )
    assert result["created"] is True
    assert result["dry_run"] is False
    rules = db.get_alert_rules(rule_type="print")
    assert len(rules) == 1
    assert rules[0]["min_notional"] == 25000
    assert rules[0]["wallet_address"] == "0xabc"
    assert db.get_recent_alerts() == []


def test_run_print_once_fires_and_stores_lagged_alert(tmp_path):
    payload = [{
        "proxyWallet": "0xwhale",
        "side": "BUY",
        "size": "20000",
        "price": "0.6",
        "slug": "bitcoin-100k",
        "title": "Bitcoin 100k",
        "timestamp": 1700000000,
        "transactionHash": "0xtx",
    }]
    db, engine = _engine(tmp_path, payload)
    result = engine.run_print_once(min_notional=10000, dry_run=False)
    assert result["triggered"] is True
    assert result["matched"] == 1
    assert result["source"] == SOURCE
    assert result["lagged"] is True
    assert QUALITY_FLAG in result["quality_flags"]
    assert "live_data_api_trades" not in result["quality_flags"]
    assert result["prints"][0]["wallet"] == "0xwhale"
    stored = db.get_recent_alerts(alert_type="print")
    assert len(stored) == 1
    assert stored[0].alert_type == "print"
    assert stored[0].wallet_address == "0xwhale"
    assert stored[0].data["print"]["lagged"] is True


def test_run_print_once_dry_run_does_not_insert(tmp_path):
    payload = [{
        "proxyWallet": "0xwhale",
        "size": "20000",
        "price": "0.6",
        "transactionHash": "0xtx",
    }]
    db, engine = _engine(tmp_path, payload)
    result = engine.run_print_once(min_notional=10000, dry_run=True)
    assert result["triggered"] is True
    assert result["dry_run"] is True
    assert result["alerts"]
    assert db.get_recent_alerts() == []


def test_run_print_once_empty_tape_does_not_invent_prints(tmp_path):
    db, engine = _engine(tmp_path, [])
    result = engine.run_print_once(min_notional=10000)
    assert result["triggered"] is False
    assert result["prints"] == []
    assert result["fetched"] == 0
    assert result["lagged"] is True
    assert QUALITY_FLAG in result["quality_flags"]
    assert db.get_recent_alerts() == []


def test_run_print_once_error_raises(tmp_path):
    db, engine = _engine(tmp_path, ConnectionError("data api down"))
    with pytest.raises(ConnectionError, match="data api down"):
        engine.run_print_once(min_notional=10000)
    assert db.get_recent_alerts() == []


def test_run_print_once_skips_below_min_notional(tmp_path):
    payload = [{
        "proxyWallet": "0xsmall",
        "size": "10",
        "price": "0.5",
        "transactionHash": "0xtx",
    }]
    db, engine = _engine(tmp_path, payload)
    result = engine.run_print_once(min_notional=10000)
    assert result["triggered"] is False
    assert result["fetched"] == 1
    assert result["matched"] == 0
    assert db.get_recent_alerts() == []
