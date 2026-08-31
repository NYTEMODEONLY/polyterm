"""Tests for lagged Data API print ingest. No live network."""

import pytest

from polyterm.api.data_api_lag import QUALITY_FLAG, SOURCE
from polyterm.core.print_scanner import (
    PrintScanner,
    match_prints,
    normalize_print,
)


def test_normalize_print_keeps_given_fields_and_stamps_lag():
    row = normalize_print({
        "proxyWallet": "0xabc",
        "side": "BUY",
        "size": "100",
        "price": "0.50",
        "timestamp": 1700000000,
        "conditionId": "0xcond",
        "slug": "bitcoin-100k",
        "title": "Bitcoin 100k",
        "transactionHash": "0xtx",
    })
    assert row is not None
    assert row["wallet"] == "0xabc"
    assert row["side"] == "BUY"
    assert row["size"] == 100.0
    assert row["price"] == 0.5
    assert row["notional"] == 50.0
    assert row["timestamp"] == 1700000000
    assert row["condition_id"] == "0xcond"
    assert row["market_slug"] == "bitcoin-100k"
    assert row["source"] == SOURCE
    assert row["lag"] is True
    assert row["lagged"] is True
    assert "lag_seconds" not in row
    assert "lag_ms" not in row


def test_normalize_print_omits_missing_fields():
    row = normalize_print({
        "size": "10",
        "price": "0.4",
        "transactionHash": "0xtx",
    })
    assert row is not None
    assert "wallet" not in row
    assert "side" not in row
    assert "timestamp" not in row
    assert "market_id" not in row
    assert row["notional"] == 4.0
    assert row["lagged"] is True


def test_normalize_print_skips_non_trade_activity():
    assert normalize_print({"type": "SPLIT", "size": "10", "price": "0.5"}) is None
    assert normalize_print({"type": "redeem", "usdcSize": "5000"}) is None
    assert normalize_print("not a mapping") is None
    assert normalize_print({"title": "no fill fields"}) is None


def test_normalize_print_skips_malformed_size_price_without_fill_evidence():
    assert normalize_print({"size": "nope", "price": "nope"}) is None


def test_match_prints_min_notional_market_and_wallet():
    prints = [
        normalize_print({
            "proxyWallet": "0xaaa",
            "size": "1000",
            "price": "0.5",
            "slug": "bitcoin-100k",
            "transactionHash": "0x1",
        }),
        normalize_print({
            "proxyWallet": "0xbbb",
            "size": "10",
            "price": "0.5",
            "slug": "bitcoin-100k",
            "transactionHash": "0x2",
        }),
        normalize_print({
            "proxyWallet": "0xaaa",
            "size": "1000",
            "price": "0.8",
            "slug": "other-market",
            "transactionHash": "0x3",
        }),
    ]
    matched = match_prints(prints, min_notional=100, market="bitcoin-100k", wallet="0xaaa")
    assert len(matched) == 1
    assert matched[0]["transaction_hash"] == "0x1"


def test_match_prints_skips_unknown_notional():
    row = normalize_print({"transactionHash": "0xtx", "side": "BUY"})
    assert row is not None
    assert "notional" not in row
    assert match_prints([row], min_notional=1) == []


class _FakeDataAPI:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    def get_recent_trades(self, **kwargs):
        self.calls.append(("recent", kwargs))
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload

    def get_trades(self, **kwargs):
        self.calls.append(("trades", kwargs))
        if isinstance(self.payload, Exception):
            raise self.payload
        return self.payload


def test_fetch_prints_success_labels_lagged_data_api():
    client = _FakeDataAPI([
        {
            "proxyWallet": "0xabc",
            "size": "200",
            "price": "0.6",
            "side": "BUY",
            "slug": "bitcoin-100k",
            "timestamp": 1700000000,
            "transactionHash": "0xtx",
        },
        {"type": "MERGE", "size": "999", "price": "1"},
    ])
    scanner = PrintScanner(data_api=client)
    payload = scanner.fetch_prints(min_notional=50, limit=10)
    assert payload["source"] == SOURCE
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert payload["fetched"] == 2
    assert payload["skipped"] == 1
    assert payload["count"] == 1
    assert payload["prints"][0]["notional"] == 120.0
    assert client.calls[0][0] == "recent"
    assert client.calls[0][1]["filter_type"] == "CASH"
    assert client.calls[0][1]["filter_amount"] == 50


def test_fetch_prints_empty_is_empty_tape_not_invented():
    scanner = PrintScanner(data_api=_FakeDataAPI([]))
    payload = scanner.fetch_prints(min_notional=10000)
    assert payload["prints"] == []
    assert payload["fetched"] == 0
    assert payload["count"] == 0
    assert "empty_data_api_page" in payload["quality_flags"]
    assert QUALITY_FLAG in payload["quality_flags"]


def test_fetch_prints_malformed_mapping_raises():
    scanner = PrintScanner(data_api=_FakeDataAPI({"error": "bad tape"}))
    with pytest.raises(RuntimeError, match="bad tape"):
        scanner.fetch_prints(min_notional=1000)


def test_fetch_prints_error_raises():
    scanner = PrintScanner(data_api=_FakeDataAPI(ConnectionError("data api down")))
    with pytest.raises(ConnectionError, match="data api down"):
        scanner.fetch_prints(min_notional=1000)


def test_scan_uses_wallet_trades_endpoint():
    client = _FakeDataAPI([
        {
            "user": "0xabc",
            "size": "400",
            "price": "0.5",
            "conditionId": "0xcond",
            "transactionHash": "0xtx",
        }
    ])
    scanner = PrintScanner(data_api=client)
    payload = scanner.scan(min_notional=100, wallet="0xabc", market="0xcond", limit=5)
    assert payload["matched"] == 1
    assert client.calls[0][0] == "trades"
    assert client.calls[0][1]["address"] == "0xabc"
    assert client.calls[0][1]["market"] == "0xcond"
    assert payload["lagged"] is True
