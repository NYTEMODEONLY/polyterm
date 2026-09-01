"""Watch-loop prints, book labels, and notify gating. No network."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

from polyterm.api.data_api_lag import QUALITY_FLAG
from polyterm.core.print_scanner import PrintScanner, normalize_print
from polyterm.core.uma_tracker import GRADE_FIELDS
from polyterm.core.watch_loop import (
    WatchBookSession,
    build_book_payload,
    collect_watch_surfaces,
    dispatch_watch_notifications,
    empty_prints_payload,
    fetch_watch_prints,
    new_notify_state,
    notify_events_from_scan,
    watch_print_market_id,
)
from polyterm.core.ws_book_freshness import WS_STALE_BANNER, WS_STALE_FLAG


NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


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


def test_empty_prints_payload_is_lagged_not_invented():
    payload = empty_prints_payload()
    assert payload["prints"] == []
    assert payload["count"] == 0
    assert payload["lag"] is True
    assert payload["lagged"] is True
    assert payload["source"] == "data_api"
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]


def test_fetch_watch_prints_labels_lagged_data_api():
    client = _FakeDataAPI([
        {
            "proxyWallet": "0xabc",
            "size": "200",
            "price": "0.5",
            "side": "BUY",
            "conditionId": "0xcond",
            "transactionHash": "0xtx",
            "timestamp": 1700000000,
        },
        {"type": "MERGE", "size": "9", "price": "1"},
    ])
    scanner = PrintScanner(data_api=client)
    payload = fetch_watch_prints(
        scanner,
        {"conditionId": "0xcond", "slug": "bitcoin-100k"},
        "bitcoin",
        limit=8,
    )
    assert payload["lagged"] is True
    assert QUALITY_FLAG in payload["quality_flags"]
    assert "live_data_api_trades" not in payload["quality_flags"]
    assert payload["count"] == 1
    assert payload["prints"][0]["notional"] == 100.0
    assert client.calls[0][0] == "trades"
    assert client.calls[0][1]["market"] == "0xcond"


def test_fetch_watch_prints_empty_tape_stays_empty():
    scanner = PrintScanner(data_api=_FakeDataAPI([]))
    payload = fetch_watch_prints(scanner, {"conditionId": "0xcond"}, "bitcoin")
    assert payload["prints"] == []
    assert payload["count"] == 0
    assert "empty_data_api_page" in payload["quality_flags"]
    assert QUALITY_FLAG in payload["quality_flags"]


def test_fetch_watch_prints_error_is_unavailable_not_fake_tape():
    scanner = PrintScanner(data_api=_FakeDataAPI(RuntimeError("data api down")))
    payload = fetch_watch_prints(scanner, {"slug": "bitcoin-100k"}, "bitcoin")
    assert payload["prints"] == []
    assert "prints_unavailable" in payload["quality_flags"]
    assert payload.get("prints_error")
    assert QUALITY_FLAG in payload["quality_flags"]


def test_watch_print_market_id_prefers_condition_id():
    ident = watch_print_market_id(
        {"id": "99", "conditionId": "0xcond", "slug": "bitcoin-100k"},
        "bitcoin",
    )
    assert ident == "0xcond"


def test_rest_book_error_is_labeled_unavailable():
    payload = build_book_payload(
        tracker=None,
        rest_book=None,
        token_id="tok-yes",
        rest_error="404 Client Error",
        now=NOW,
    )
    assert payload["source"] == "none"
    assert payload["live"] is False
    assert payload["rest_error"] == "404 Client Error"
    assert "clob_rest_unavailable" in payload["quality_flags"]


def test_rest_book_payload_is_not_live():
    clob = Mock()
    clob.get_order_book.return_value = {
        "bids": [{"price": "0.44", "size": "10"}],
        "asks": [{"price": "0.45", "size": "12"}],
    }
    surfaces = collect_watch_surfaces(
        market="bitcoin",
        gamma_client=None,
        clob_client=clob,
        print_scanner=PrintScanner(data_api=_FakeDataAPI([])),
        market_data={"clobTokenIds": ["tok-yes"], "conditionId": "0xcond"},
        now=NOW,
    )
    book = surfaces["book"]
    assert book["source"] == "clob_rest"
    assert book["live"] is False
    assert book["ws_stale"] is False
    assert book["best_bid"] == 0.44
    assert book["best_ask"] == 0.45
    assert surfaces["prints"]["lagged"] is True
    resolution = surfaces["resolution"]
    assert resolution["status"] == "none"
    assert "uma_unavailable" in resolution["quality_flags"]
    for key in GRADE_FIELDS:
        assert key not in resolution


def test_collect_watch_surfaces_includes_gamma_resolution():
    clob = Mock()
    clob.get_order_book.return_value = {"bids": [], "asks": []}
    surfaces = collect_watch_surfaces(
        market="bitcoin",
        gamma_client=None,
        clob_client=clob,
        print_scanner=PrintScanner(data_api=_FakeDataAPI([])),
        market_data={
            "clobTokenIds": ["tok-yes"],
            "conditionId": "0xcond",
            "umaResolutionStatus": "disputed",
            "umaResolutionStatuses": '["proposed", "disputed"]',
            "acceptingOrders": True,
            "closed": False,
        },
        now=NOW,
    )
    resolution = surfaces["resolution"]
    assert resolution["status"] == "disputed"
    assert resolution["disputed"] is True
    assert resolution["trading"] == "open_for_trading"
    assert resolution["redeemable"] is False
    assert "hours_remaining" not in resolution
    assert "missing_timestamps" in resolution["quality_flags"]
    for key in GRADE_FIELDS:
        assert key not in resolution
    assert "fairness" not in str(resolution).lower()


def test_frozen_ws_session_uses_rest_fallback_and_banner():
    clob = Mock()
    clob.get_order_book.return_value = {
        "bids": [{"price": "0.50", "size": "1"}],
        "asks": [{"price": "0.51", "size": "1"}],
    }
    session = WatchBookSession(clob, ["tok-yes"], stale_after_seconds=15)
    session.tracker.mark_connected(True, at=NOW - timedelta(seconds=40))
    session.note_ws_message({"type": "PONG"})
    payload = session.snapshot(now=NOW)
    assert payload["ws_connected"] is True
    assert payload["ws_stale"] is True
    assert payload["live"] is False
    assert payload["source"] == "clob_rest"
    assert payload["banner"] == WS_STALE_BANNER
    assert WS_STALE_FLAG in payload["quality_flags"]
    clob.get_order_book.assert_called()


def test_build_book_payload_live_ws_skips_calling_it_rest():
    session = WatchBookSession(Mock(), ["tok-yes"], stale_after_seconds=20)
    session.tracker.mark_connected(True, at=NOW - timedelta(seconds=5))
    session.note_ws_message({
        "type": "book",
        "bids": [{"price": "0.61", "size": "3"}],
        "asks": [{"price": "0.62", "size": "4"}],
    },)
    session.tracker.last_tick_at = NOW - timedelta(seconds=1)
    payload = build_book_payload(
        tracker=session.tracker,
        rest_book=None,
        token_id="tok-yes",
        now=NOW,
        ws_book={
            "bids": [{"price": "0.61", "size": "3"}],
            "asks": [{"price": "0.62", "size": "4"}],
        },
    )
    assert payload["live"] is True
    assert payload["source"] == "clob_ws"
    assert payload["ws_stale"] is False


def test_notify_events_only_on_matching_prints_and_shifts():
    print_row = normalize_print({
        "proxyWallet": "0xabc",
        "size": "1000",
        "price": "0.5",
        "transactionHash": "0xtx",
        "side": "BUY",
    })
    small = normalize_print({
        "proxyWallet": "0xabc",
        "size": "1",
        "price": "0.5",
        "transactionHash": "0xsmall",
        "side": "SELL",
    })
    payload = {
        "prints": [print_row, small],
        "lagged": True,
    }
    state = new_notify_state()
    events = notify_events_from_scan(
        payload,
        [{"market_id": "m1", "title": "Bitcoin", "shift_type": ["probability"]}],
        min_notional=100,
        state=state,
    )
    kinds = [item["kind"] for item in events]
    assert kinds == ["print", "threshold"]
    assert "0xtx" in events[0]["id"]
    again = notify_events_from_scan(payload, [
        {"market_id": "m1", "title": "Bitcoin", "shift_type": ["probability"]},
    ], min_notional=100, state=state)
    assert again == []


def test_notify_not_fired_on_empty_poll():
    events = notify_events_from_scan({"prints": []}, [], min_notional=10000)
    assert events == []
    sent = dispatch_watch_notifications("telegram", events, Mock())
    assert sent == []


def test_dispatch_watch_notifications_uses_requested_channel_only():
    manager = Mock()
    manager.send.return_value = {"telegram": True}
    events = [{
        "kind": "print",
        "id": "tx:0xtx",
        "title": "Lagged Data API print",
        "message": "Lagged Data API print $500",
        "level": "warning",
        "data": {"notional": 500},
    }]
    sent = dispatch_watch_notifications("telegram", events, manager)
    assert sent == [{
        "kind": "print",
        "id": "tx:0xtx",
        "channel": "telegram",
        "sent": True,
    }]
    manager.send.assert_called_once()
