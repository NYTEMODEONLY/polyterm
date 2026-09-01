"""Honest UMA/resolution snapshots. No invented fairness grades."""

from datetime import datetime, timezone

from polyterm.core.uma_tracker import (
    GRADE_FIELDS,
    UMADisputeTracker,
    resolution_dashboard_line,
    snapshot_market_resolution,
)


NOW = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _assert_no_grade(payload):
    for key in GRADE_FIELDS:
        assert key not in payload
    blob = str(payload).lower()
    assert "fairness" not in blob
    assert "letter grade" not in blob


def test_snapshot_disputed_market_without_inventing_window():
    payload = snapshot_market_resolution(
        {
            "id": "m1",
            "umaResolutionStatus": "disputed",
            "umaResolutionStatuses": '["proposed", "disputed"]',
            "acceptingOrders": True,
            "closed": False,
            "resolvedBy": "0xadapter",
            "customLiveness": 0,
        },
        now=NOW,
    )
    assert payload["status"] == "disputed"
    assert payload["disputed"] is True
    assert payload["uma_resolution_statuses"] == ["proposed", "disputed"]
    assert payload["accepting_orders"] is True
    assert payload["trading"] == "open_for_trading"
    assert payload["redeemable"] is False
    assert "proposer" not in payload
    assert payload["resolved_by"] == "0xadapter"
    assert "hours_remaining" not in payload
    assert "missing_timestamps" in payload["quality_flags"]
    assert "uma_unavailable" not in payload["quality_flags"]
    _assert_no_grade(payload)


def test_snapshot_proposed_with_real_deadline_hours():
    payload = snapshot_market_resolution(
        {
            "umaResolutionStatus": "proposed",
            "umaResolutionStatuses": ["proposed"],
            "umaEndDate": "2026-06-01T14:30:00Z",
            "acceptingOrders": False,
            "closed": False,
            "proposer": "0xproposer",
        },
        now=NOW,
    )
    assert payload["status"] == "proposed"
    assert payload["disputed"] is False
    assert payload["proposer"] == "0xproposer"
    assert payload["hours_remaining"] == 2.5
    assert payload["trading"] == "not_accepting_orders"
    assert payload["redeemable"] is False
    assert "missing_timestamps" not in payload["quality_flags"]
    _assert_no_grade(payload)


def test_snapshot_pending_uses_gamma_status():
    payload = snapshot_market_resolution(
        {
            "umaResolutionStatus": "pending",
            "closed": True,
            "acceptingOrders": False,
        },
        now=NOW,
    )
    assert payload["status"] == "pending"
    assert payload["disputed"] is False
    assert payload["trading"] == "closed"
    assert payload["redeemable"] is False
    assert "missing_timestamps" in payload["quality_flags"]
    _assert_no_grade(payload)


def test_snapshot_none_when_uma_fields_missing():
    payload = snapshot_market_resolution(
        {
            "id": "m1",
            "question": "Bitcoin 100k?",
            "acceptingOrders": True,
            "closed": False,
            "umaResolutionStatuses": [],
        },
        now=NOW,
    )
    assert payload["status"] == "none"
    assert payload["disputed"] is False
    assert payload["trading"] == "open_for_trading"
    assert payload["redeemable"] is False
    assert "uma_unavailable" in payload["quality_flags"]
    assert "hours_remaining" not in payload
    _assert_no_grade(payload)


def test_snapshot_missing_market_is_uma_unavailable():
    payload = snapshot_market_resolution(None, now=NOW)
    assert payload["status"] == "none"
    assert payload["disputed"] is False
    assert "uma_unavailable" in payload["quality_flags"]
    assert "trading" not in payload
    _assert_no_grade(payload)


def test_snapshot_malformed_statuses_and_timestamp():
    payload = snapshot_market_resolution(
        {
            "umaResolutionStatus": "disputed",
            "umaResolutionStatuses": "{not-json",
            "umaEndDate": "July 19, 2022",
            "acceptingOrders": "sometimes",
            "closed": True,
        },
        now=NOW,
    )
    assert payload["status"] == "disputed"
    assert "uma_resolution_statuses" not in payload
    assert "hours_remaining" not in payload
    assert "unparsed_timestamp" in payload["quality_flags"]
    assert "malformed_uma_fields" in payload["quality_flags"]
    assert "missing_timestamps" in payload["quality_flags"]
    assert "accepting_orders" not in payload
    assert payload["closed"] is True
    assert payload["trading"] == "closed"
    _assert_no_grade(payload)


def test_snapshot_resolved_is_redeemable_without_grade():
    payload = snapshot_market_resolution(
        {
            "umaResolutionStatus": "resolved",
            "umaResolutionStatuses": '["proposed", "resolved"]',
            "closed": True,
            "acceptingOrders": False,
            "automaticallyResolved": True,
            "umaEndDate": "2026-05-01T12:00:00Z",
            "closedTime": "2026-05-01 12:00:00+00",
        },
        now=NOW,
    )
    assert payload["status"] == "resolved"
    assert payload["disputed"] is False
    assert payload["redeemable"] is True
    assert payload["trading"] == "closed"
    assert payload["hours_since_uma_end"] == 744.0
    assert "hours_remaining" not in payload
    _assert_no_grade(payload)


def test_custom_liveness_zero_does_not_invent_hours():
    payload = snapshot_market_resolution(
        {
            "umaResolutionStatus": "proposed",
            "customLiveness": 0,
            "acceptingOrdersTimestamp": "2026-05-01T12:00:00Z",
        },
        now=NOW,
    )
    assert payload["liveness_seconds"] == 0.0
    assert "hours_remaining" not in payload
    assert "missing_timestamps" in payload["quality_flags"]
    _assert_no_grade(payload)


def test_dashboard_line_is_short_and_ungraded():
    disputed = snapshot_market_resolution(
        {
            "umaResolutionStatus": "disputed",
            "acceptingOrders": True,
            "closed": False,
        },
        now=NOW,
    )
    line = resolution_dashboard_line(disputed)
    assert "UMA: disputed" in line
    assert "open for trading" in line
    assert "window unknown" in line
    assert "low" not in line.lower()
    assert "grade" not in line.lower()

    none_line = resolution_dashboard_line(snapshot_market_resolution({}, now=NOW))
    assert "uma unavailable" in none_line
    assert "UMA: none" in none_line


def test_watch_snapshot_does_not_call_risk_heuristic():
    """The watch helper is a field copy. Risk scoring stays on polyterm risk."""
    tracker = UMADisputeTracker()
    market = {
        "umaResolutionStatus": "disputed",
        "question": "Will this be the most significant historic outcome?",
        "description": "Best and most important result.",
        "closed": False,
        "acceptingOrders": True,
    }
    payload = snapshot_market_resolution(market, now=NOW)
    analysis = tracker.analyze_resolution_risk(
        market_id="m1",
        title=market["question"],
        description=market["description"],
    )
    assert payload["status"] == "disputed"
    assert "risk_score" in analysis.to_dict()
    _assert_no_grade(payload)
