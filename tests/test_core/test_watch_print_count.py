"""Session lagged-print count from the existing watch tape. No network."""

from polyterm.core.watch_print_count import (
    SESSION_COUNT_KEY,
    WatchPrintSession,
    payload_print_count,
    print_rows_from_payload,
    session_print_count_value,
    stamp_session_print_count,
    watch_print_count_dashboard_line,
)


def _print_row(tx, notional=12000):
    return {
        "wallet": "0xabc",
        "side": "BUY",
        "notional": notional,
        "transaction_hash": tx,
        "source": "data_api",
        "lag": True,
        "lagged": True,
    }


def test_empty_tape_is_zero_not_synthetic_rows():
    payload = {"prints": [], "count": 0}
    assert print_rows_from_payload(payload) == []
    assert payload_print_count(payload) == 0
    assert payload_print_count(None) == 0
    assert payload_print_count({}) == 0
    assert payload_print_count({"prints": [None, "x", 1]}) == 0
    stamped = stamp_session_print_count(payload)
    assert stamped[SESSION_COUNT_KEY] == 0
    assert stamped["prints"] == []
    assert watch_print_count_dashboard_line(stamped) == "prints this session: 0"


def test_one_print_counts_as_one():
    payload = {"prints": [_print_row("0xtx1")], "count": 1}
    stamped = stamp_session_print_count(payload)
    assert stamped[SESSION_COUNT_KEY] == 1
    assert stamped["prints"][0]["transaction_hash"] == "0xtx1"
    assert "wallet" not in stamp_session_print_count({"prints": []})
    assert watch_print_count_dashboard_line(stamped) == "prints this session: 1"


def test_several_prints_count_each_real_row():
    payload = {
        "prints": [
            _print_row("0xtx1"),
            _print_row("0xtx2", notional=8000),
            _print_row("0xtx3"),
        ],
        "count": 3,
    }
    stamped = stamp_session_print_count(payload)
    assert stamped[SESSION_COUNT_KEY] == 3
    assert len(stamped["prints"]) == 3
    assert watch_print_count_dashboard_line(stamped) == "prints this session: 3"


def test_session_accumulates_unique_prints_and_skips_repeats():
    session = WatchPrintSession()
    assert session.count == 0
    first = stamp_session_print_count({"prints": []}, session)
    assert first[SESSION_COUNT_KEY] == 0
    second = stamp_session_print_count(
        {"prints": [_print_row("0xtx1")]},
        session,
    )
    assert second[SESSION_COUNT_KEY] == 1
    again = stamp_session_print_count(
        {"prints": [_print_row("0xtx1")]},
        session,
    )
    assert again[SESSION_COUNT_KEY] == 1
    more = stamp_session_print_count(
        {"prints": [_print_row("0xtx1"), _print_row("0xtx2"), _print_row("0xtx3")]},
        session,
    )
    assert more[SESSION_COUNT_KEY] == 3
    assert session_print_count_value(more) == 3


def test_count_does_not_invent_wallets_or_notionals():
    payload = {
        "prints": [{
            "transaction_hash": "0xtxbare",
            "source": "data_api",
            "lagged": True,
        }],
    }
    stamped = stamp_session_print_count(payload)
    assert stamped[SESSION_COUNT_KEY] == 1
    row = stamped["prints"][0]
    assert "wallet" not in row
    assert "notional" not in row
    assert row["transaction_hash"] == "0xtxbare"
