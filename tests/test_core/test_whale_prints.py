"""Tests for wallet-level lagged Data API prints. No live network."""

from datetime import datetime, timezone

from polyterm.api.data_api_lag import QUALITY_FLAG, SOURCE
from polyterm.core.print_scanner import PrintScanner, normalize_print
from polyterm.core.whale_prints import (
    DEFAULT_PRINT_MIN_NOTIONAL,
    rollup_prints_by_wallet,
    scan_whale_prints,
)


INSIDER_KEYS = (
    "insider_score",
    "insider",
    "risk_score",
    "win_rate",
    "syndicate",
    "copy",
)


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


def _trade(wallet="0xabc", size="20000", price="0.50", slug="bitcoin-100k", ts=1700000000, tx="0xtx"):
    return {
        "proxyWallet": wallet,
        "side": "BUY",
        "size": size,
        "price": price,
        "slug": slug,
        "title": slug,
        "timestamp": ts,
        "transactionHash": tx,
    }


def _assert_lagged_no_insider(payload):
    assert payload["source"] == SOURCE
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    for key in INSIDER_KEYS:
        assert key not in payload
    for row in payload.get("prints") or []:
        for key in INSIDER_KEYS:
            assert key not in row
    for wallet in payload.get("wallets") or []:
        for key in INSIDER_KEYS:
            assert key not in wallet


def test_default_print_floor_matches_watch_alerts():
    assert DEFAULT_PRINT_MIN_NOTIONAL == 10000.0


def test_scan_whale_prints_labels_lagged_data_api_and_rolls_up_wallets():
    client = _FakeDataAPI([
        _trade(wallet="0xaaa", size="40000", price="0.5", tx="0x1"),
        _trade(wallet="0xbbb", size="30000", price="0.5", tx="0x2"),
        _trade(wallet="0xaaa", size="20000", price="0.5", tx="0x3"),
        {"type": "SPLIT", "size": "99999", "price": "1"},
    ])
    now = datetime.fromtimestamp(1700000000, timezone.utc)
    payload = scan_whale_prints(
        scanner=PrintScanner(data_api=client),
        min_notional=10000,
        hours=24,
        limit=10,
        now=now,
    )
    _assert_lagged_no_insider(payload)
    assert payload["mode"] == "wallet_trades"
    assert payload["min_notional"] == 10000
    assert payload["matched"] == 3
    assert payload["count"] == 3
    assert len(payload["prints"]) == 3
    assert payload["prints"][0]["source"] == SOURCE
    assert payload["prints"][0]["lagged"] is True
    assert payload["wallet_count"] == 2
    assert payload["wallets"][0]["address"] == "0xaaa"
    assert payload["wallets"][0]["trade_count"] == 2
    assert payload["wallets"][0]["notional"] == 30000.0
    assert client.calls[0][0] == "recent"
    assert client.calls[0][1]["filter_type"] == "CASH"
    assert client.calls[0][1]["filter_amount"] == 10000


def test_empty_tape_is_empty_not_synthetic_whales():
    payload = scan_whale_prints(
        scanner=PrintScanner(data_api=_FakeDataAPI([])),
        min_notional=10000,
        hours=24,
        limit=20,
    )
    _assert_lagged_no_insider(payload)
    assert payload["prints"] == []
    assert payload["wallets"] == []
    assert payload["count"] == 0
    assert payload["wallet_count"] == 0
    assert payload["fetched"] == 0
    assert "empty_data_api_page" in payload["quality_flags"]


def test_below_min_notional_does_not_invent_wallets():
    client = _FakeDataAPI([_trade(size="10", price="0.5", tx="0xsmall")])
    payload = scan_whale_prints(
        scanner=PrintScanner(data_api=client),
        min_notional=10000,
        hours=24,
        now=datetime.fromtimestamp(1700000000, timezone.utc),
    )
    assert payload["prints"] == []
    assert payload["wallets"] == []
    assert "no_prints_at_min_notional" in payload["quality_flags"]
    _assert_lagged_no_insider(payload)


def test_hours_filter_drops_old_prints_without_inventing_timestamps():
    old_ts = 1700000000 - (100 * 3600)
    client = _FakeDataAPI([
        _trade(wallet="0xnew", ts=1700000000, tx="0xnew"),
        _trade(wallet="0xold", ts=old_ts, tx="0xold"),
        {
            "proxyWallet": "0xnotime",
            "side": "BUY",
            "size": "20000",
            "price": "0.5",
            "transactionHash": "0xnotime",
        },
    ])
    payload = scan_whale_prints(
        scanner=PrintScanner(data_api=client),
        min_notional=10000,
        hours=24,
        now=datetime.fromtimestamp(1700000000, timezone.utc),
    )
    wallets = {row["address"] for row in payload["wallets"]}
    txes = {row.get("transaction_hash") for row in payload["prints"]}
    assert "0xold" not in txes
    assert "0xnew" in txes
    assert "0xnotime" in txes
    assert "0xold" not in wallets
    assert "dropped_prints_outside_hours" in payload["quality_flags"]


def test_missing_wallet_is_not_invented_in_rollup():
    prints = [
        normalize_print(_trade(wallet="0xabc", tx="0x1")),
        normalize_print({
            "size": "20000",
            "price": "0.5",
            "transactionHash": "0xnowallet",
            "timestamp": 1700000000,
        }),
    ]
    wallets = rollup_prints_by_wallet(prints)
    assert len(wallets) == 1
    assert wallets[0]["address"] == "0xabc"
    assert all(item["address"] != "unknown" for item in wallets)


def test_scan_strips_live_data_api_trades_misnomer():
    payload = scan_whale_prints(
        scanner=PrintScanner(data_api=_FakeDataAPI([])),
        min_notional=DEFAULT_PRINT_MIN_NOTIONAL,
    )
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert QUALITY_FLAG in payload["quality_flags"]
