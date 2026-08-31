"""Core tests for CLOB price-history series vs labeled demo walk."""

from datetime import datetime, timezone

import pytest

from polyterm.core.price_history import (
    DEMO_DISCLOSURE,
    SOURCE_CLOB,
    SOURCE_DEMO,
    SOURCE_NONE,
    build_clob_payload,
    build_demo_payload,
    build_demo_points,
    build_time_bounds,
    parse_clob_history_rows,
    period_to_hours,
    refuse_payload,
    select_clob_granularity,
    summarize_series,
)


def test_period_to_hours_and_granularity():
    assert period_to_hours("day") == 24
    assert period_to_hours("week") == 168
    assert period_to_hours("month") == 720
    assert period_to_hours("all") == 2160
    assert select_clob_granularity(24) == ("1d", 300)
    assert select_clob_granularity(168) == ("max", 3600)


def test_parse_clob_history_rows_keeps_in_window_points():
    now = datetime(2026, 8, 30, 12, tzinfo=timezone.utc)
    start_ts, end_ts = build_time_bounds(24, now=now)
    rows = [
        {"t": start_ts - 60, "p": "0.10"},
        {"t": start_ts + 60, "p": "0.40"},
        {"t": start_ts + 120, "p": "0.55"},
        {"t": end_ts + 60, "p": "0.90"},
        {"t": "bad", "p": "0.50"},
        {"missing": True},
    ]
    points = parse_clob_history_rows(rows, start_ts, end_ts)
    assert [point["price"] for point in points] == [0.40, 0.55]
    assert all("timestamp" in point and "date" in point for point in points)


def test_summarize_series_uses_real_high_low_and_change():
    points = [
        {"timestamp": "2026-08-23T00:00:00+00:00", "date": "08/23", "price": 0.40},
        {"timestamp": "2026-08-24T00:00:00+00:00", "date": "08/24", "price": 0.70},
        {"timestamp": "2026-08-25T00:00:00+00:00", "date": "08/25", "price": 0.55},
    ]
    series = summarize_series(points, current_price=0.55, reported_volume=1200)
    assert series["summary"]["high"] == 0.70
    assert series["summary"]["low"] == 0.40
    assert series["summary"]["price_change"] == pytest.approx(0.15)
    assert series["summary"]["reported_volume"] == 1200
    assert series["trend"]["direction"] in {"up", "down", "sideways"}
    types = {item["type"] for item in series["milestones"]}
    assert "high" in types
    assert "low" in types


def test_clob_payload_is_marked_historical():
    points = [
        {"timestamp": "2026-08-23T00:00:00+00:00", "date": "08/23", "price": 0.41},
        {"timestamp": "2026-08-24T00:00:00+00:00", "date": "08/24", "price": 0.44},
    ]
    payload = build_clob_payload(
        points,
        market_title="Will BTC hit 100k?",
        period="week",
        hours=168,
        token_id="token-yes",
        gamma_market_id="market-1",
    )
    assert payload["success"] is True
    assert payload["uses_historical_data"] is True
    assert payload["source"] == SOURCE_CLOB
    assert payload["clob_token_id"] == "token-yes"
    assert payload["point_count"] == 2
    assert payload["history"]["points"][0]["price"] == 0.41


def test_demo_payload_is_labeled_and_not_historical():
    payload = build_demo_payload(
        market_title="Demo market",
        period="week",
        current_price=0.55,
        seed_key="demo:week",
    )
    assert payload["success"] is True
    assert payload["uses_historical_data"] is False
    assert payload["source"] == SOURCE_DEMO
    assert payload["disclosure"] == DEMO_DISCLOSURE
    assert payload["point_count"] == len(payload["history"]["points"])
    assert payload["history"]["points"][-1]["price"] == 0.55
    again = build_demo_points(0.55, 168, seed_key="demo:week")
    assert [point["price"] for point in again] == [
        point["price"] for point in payload["history"]["points"]
    ]


def test_refuse_payload_has_evidence_flags():
    payload = refuse_payload("No CLOB price history is available for this market.")
    assert payload["success"] is False
    assert payload["uses_historical_data"] is False
    assert payload["source"] == SOURCE_NONE
    assert payload["mode"] == "unavailable"
    assert "history" not in payload
