"""Frozen CLOB WS vs live book ticks. No network."""

from datetime import datetime, timedelta, timezone

from polyterm.core.ws_book_freshness import (
    CLOB_REST_SOURCE,
    CLOB_WS_SOURCE,
    DEFAULT_STALE_AFTER_SECONDS,
    WS_STALE_BANNER,
    WS_STALE_FLAG,
    BookTickTracker,
    assess_book_freshness,
    is_book_tick,
)


NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def test_ping_and_tick_size_are_not_book_ticks():
    assert is_book_tick({"type": "PING"}) is False
    assert is_book_tick({"type": "PONG"}) is False
    assert is_book_tick({"type": "tick_size_change"}) is False
    assert is_book_tick("book") is False
    assert is_book_tick({"type": "book"}) is True
    assert is_book_tick({"event_type": "price_change"}) is True
    assert is_book_tick({"type": "last_trade_price"}) is True


def test_connected_without_ticks_is_not_live_until_stale_window():
    freshness = assess_book_freshness(
        ws_connected=True,
        connected_at=NOW - timedelta(seconds=5),
        now=NOW,
        stale_after_seconds=20,
        rest_fallback=True,
        has_rest_book=True,
    )
    assert freshness.ws_connected is True
    assert freshness.ws_stale is False
    assert freshness.live is False
    assert freshness.source == CLOB_REST_SOURCE
    assert WS_STALE_FLAG not in freshness.quality_flags


def test_connected_no_ticks_after_n_seconds_is_ws_stale():
    freshness = assess_book_freshness(
        ws_connected=True,
        connected_at=NOW - timedelta(seconds=25),
        now=NOW,
        stale_after_seconds=20,
        rest_fallback=True,
        has_rest_book=True,
        token_id="tok-yes",
        best_bid=0.55,
        best_ask=0.56,
    )
    payload = freshness.to_dict()
    assert payload["ws_stale"] is True
    assert payload["live"] is False
    assert payload["source"] == CLOB_REST_SOURCE
    assert payload["banner"] == WS_STALE_BANNER
    assert WS_STALE_FLAG in payload["quality_flags"]
    assert CLOB_REST_SOURCE in payload["quality_flags"]
    assert payload["best_bid"] == 0.55


def test_recent_book_tick_is_live_clob_ws():
    freshness = assess_book_freshness(
        ws_connected=True,
        last_tick_at=NOW - timedelta(seconds=2),
        last_tick_type="book",
        now=NOW,
        stale_after_seconds=20,
    )
    payload = freshness.to_dict()
    assert payload["live"] is True
    assert payload["ws_stale"] is False
    assert payload["source"] == CLOB_WS_SOURCE
    assert payload["last_tick_type"] == "book"
    assert "banner" not in payload


def test_old_tick_while_socket_up_is_stale_not_live():
    freshness = assess_book_freshness(
        ws_connected=True,
        last_tick_at=NOW - timedelta(seconds=40),
        last_tick_type="price_change",
        now=NOW,
        stale_after_seconds=20,
        rest_fallback=False,
        has_rest_book=False,
    )
    assert freshness.live is False
    assert freshness.ws_stale is True
    assert freshness.banner == WS_STALE_BANNER
    assert freshness.source == "none"


def test_tracker_ignores_ping_then_flags_stale():
    tracker = BookTickTracker(stale_after_seconds=15)
    connected_at = NOW - timedelta(seconds=20)
    tracker.mark_connected(True, at=connected_at)
    assert tracker.note_message({"type": "PONG"}, at=NOW) is False
    assert tracker.tick_count == 0
    freshness = tracker.assess(
        now=NOW,
        rest_fallback=True,
        has_rest_book=True,
    )
    assert freshness.ws_stale is True
    assert freshness.live is False
    assert freshness.source == CLOB_REST_SOURCE


def test_tracker_book_tick_clears_stale():
    tracker = BookTickTracker(stale_after_seconds=15)
    tracker.mark_connected(True, at=NOW - timedelta(seconds=30))
    assert tracker.note_message({"type": "book", "bids": []}, at=NOW - timedelta(seconds=1))
    freshness = tracker.assess(now=NOW)
    assert freshness.live is True
    assert freshness.ws_stale is False
    assert freshness.source == CLOB_WS_SOURCE


def test_rest_only_snapshot_is_labeled_not_live():
    freshness = assess_book_freshness(
        ws_connected=False,
        now=NOW,
        rest_fallback=True,
        has_rest_book=True,
        best_bid=0.4,
        best_ask=0.41,
    )
    payload = freshness.to_dict()
    assert payload["source"] == CLOB_REST_SOURCE
    assert payload["live"] is False
    assert payload["ws_stale"] is False
    assert payload["ws_connected"] is False
    assert DEFAULT_STALE_AFTER_SECONDS == 20.0
