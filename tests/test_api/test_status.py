"""Mocked tests for the Statuspage v2 client. No live network."""

import requests
from unittest.mock import Mock

from polyterm.api.status import (
    DEFAULT_STATUS_PAGE_URL,
    STATUSPAGE_SUMMARY_PATH,
    StatusPageClient,
    parse_statuspage_summary,
    unknown_status_snapshot,
)


OPERATIONAL_SUMMARY = {
    "page": {
        "id": "page-1",
        "name": "Polymarket",
        "url": "https://status.polymarket.com",
        "updated_at": "2026-08-31T00:00:00Z",
    },
    "status": {
        "indicator": "none",
        "description": "All Systems Operational",
    },
    "components": [
        {"name": "CLOB API", "status": "operational"},
        {"name": "Markets API", "status": "operational"},
    ],
}


def test_parse_operational_indicator_none():
    snapshot = parse_statuspage_summary(OPERATIONAL_SUMMARY)
    assert snapshot.reachable is True
    assert snapshot.indicator == "none"
    assert snapshot.description == "All Systems Operational"
    assert snapshot.components[0]["name"] == "CLOB API"


def test_parse_minor_is_not_operational():
    payload = {
        "status": {"indicator": "minor", "description": "Minor Service Outage"},
        "page": {"url": DEFAULT_STATUS_PAGE_URL},
    }
    snapshot = parse_statuspage_summary(payload)
    assert snapshot.indicator == "minor"
    assert snapshot.indicator != "none"


def test_parse_missing_status_is_unknown_not_operational():
    snapshot = parse_statuspage_summary({"page": {"name": "Polymarket"}})
    assert snapshot.indicator == "status_unknown"
    assert snapshot.indicator != "none"
    assert "operational" not in snapshot.description.lower() or "unreadable" in snapshot.description.lower()


def test_parse_non_object_is_unknown():
    snapshot = parse_statuspage_summary(["not", "an", "object"])
    assert snapshot.indicator == "status_unknown"
    assert snapshot.reachable is True


def test_parse_unrecognized_indicator_is_unknown():
    snapshot = parse_statuspage_summary(
        {"status": {"indicator": "operational", "description": "All Systems Operational"}}
    )
    assert snapshot.indicator == "status_unknown"
    assert snapshot.error and "Unrecognized" in snapshot.error


def test_unknown_helper_never_claims_operational():
    snapshot = unknown_status_snapshot(reachable=False, error="timeout")
    assert snapshot.indicator == "status_unknown"
    assert snapshot.reachable is False
    assert snapshot.description != "All Systems Operational"


def test_get_summary_fetches_documented_statuspage_path():
    session = Mock()
    response = Mock()
    response.json.return_value = OPERATIONAL_SUMMARY
    response.raise_for_status.return_value = None
    session.get.return_value = response

    client = StatusPageClient(
        base_url="https://status.example.test",
        session=session,
        timeout=1,
    )
    snapshot = client.get_summary()

    session.get.assert_called_once_with(
        f"https://status.example.test{STATUSPAGE_SUMMARY_PATH}",
        timeout=1,
    )
    assert snapshot.indicator == "none"
    client.close()


def test_connection_error_is_status_unknown():
    session = Mock()
    session.get.side_effect = requests.exceptions.ConnectionError("dns fail")
    client = StatusPageClient(session=session, timeout=1)

    snapshot = client.get_summary()

    assert snapshot.reachable is False
    assert snapshot.indicator == "status_unknown"
    assert snapshot.description != "All Systems Operational"
    assert "dns fail" in (snapshot.error or "")


def test_http_error_is_status_unknown():
    session = Mock()
    response = Mock()
    response.raise_for_status.side_effect = requests.exceptions.HTTPError("503")
    session.get.return_value = response
    client = StatusPageClient(session=session, timeout=1)

    snapshot = client.get_summary()

    assert snapshot.indicator == "status_unknown"
    assert snapshot.reachable is False


def test_invalid_json_is_status_unknown():
    session = Mock()
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.side_effect = ValueError("No JSON")
    session.get.return_value = response
    client = StatusPageClient(session=session, timeout=1)

    snapshot = client.get_summary()

    assert snapshot.reachable is True
    assert snapshot.indicator == "status_unknown"
    assert "non-JSON" in (snapshot.error or "")
