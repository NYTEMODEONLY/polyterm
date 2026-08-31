"""Mocked tests for Gamma/CLOB/status-page health combining."""

from unittest.mock import Mock

from polyterm.api.status import parse_statuspage_summary, unknown_status_snapshot
from polyterm.core.service_health import (
    SourceProbe,
    assess_service_health,
    clob_trading_flags,
    combine_health,
)


def _ok_page():
    return parse_statuspage_summary({
        "status": {"indicator": "none", "description": "All Systems Operational"},
        "page": {"name": "Polymarket", "url": "https://status.polymarket.com"},
    })


def test_both_apis_fail_is_outage():
    health = combine_health(
        SourceProbe("gamma", ok=False, error="Gamma down"),
        SourceProbe("clob", ok=False, error="CLOB down"),
        _ok_page(),
    )
    assert health.mode == "outage"
    assert health.status == "outage"
    assert "both failed" in health.message
    assert "Gamma down" in health.message
    assert "CLOB down" in health.message


def test_green_status_page_does_not_hide_api_outage():
    health = combine_health(
        SourceProbe("gamma", ok=False, error="timeout"),
        SourceProbe("clob", ok=False, error="timeout"),
        _ok_page(),
    )
    assert health.mode == "outage"
    assert health.status_page.indicator == "none"


def test_one_api_fail_is_degraded():
    health = combine_health(
        SourceProbe("gamma", ok=False, error="Gamma timeout"),
        SourceProbe("clob", ok=True),
        _ok_page(),
    )
    assert health.mode == "degraded"
    assert health.status == "degraded"
    assert "Gamma" in health.message


def test_clob_only_fail_is_degraded():
    health = combine_health(
        SourceProbe("gamma", ok=True),
        SourceProbe("clob", ok=False, error="CLOB timeout"),
        _ok_page(),
    )
    assert health.status == "degraded"
    assert health.mode == "degraded"


def test_apis_ok_and_page_none_is_operational():
    health = combine_health(
        SourceProbe("gamma", ok=True),
        SourceProbe("clob", ok=True),
        _ok_page(),
    )
    assert health.mode == "operational"
    assert health.status == "operational"


def test_apis_ok_unreachable_page_is_status_unknown_not_operational():
    health = combine_health(
        SourceProbe("gamma", ok=True),
        SourceProbe("clob", ok=True),
        unknown_status_snapshot(reachable=False, error="status page timeout"),
    )
    assert health.mode == "status_unknown"
    assert health.status == "status_unknown"
    assert health.mode != "operational"


def test_status_page_major_is_outage_even_if_probes_ok():
    page = parse_statuspage_summary({
        "status": {"indicator": "major", "description": "Major Service Outage"},
    })
    health = combine_health(
        SourceProbe("gamma", ok=True),
        SourceProbe("clob", ok=True),
        page,
    )
    assert health.mode == "outage"
    assert health.status == "outage"


def test_status_page_minor_is_degraded():
    page = parse_statuspage_summary({
        "status": {"indicator": "minor", "description": "Minor Service Outage"},
    })
    health = combine_health(
        SourceProbe("gamma", ok=True),
        SourceProbe("clob", ok=True),
        page,
    )
    assert health.status == "degraded"


def test_assess_service_health_uses_client_probes():
    gamma = Mock()
    gamma.get_markets.side_effect = Exception("gamma down")
    clob = Mock()
    clob.get_current_markets.side_effect = Exception("clob down")
    status_client = Mock()
    status_client.get_summary.return_value = unknown_status_snapshot(
        reachable=False, error="offline"
    )

    health = assess_service_health(gamma, clob, status_client)

    gamma.get_markets.assert_called_once()
    clob.get_current_markets.assert_called_once()
    assert health.mode == "outage"
    assert health.status == "outage"


def test_clob_trading_flags_pass_through_accepting_orders_only():
    flags = clob_trading_flags({"accepting_orders": False, "closed": False})
    assert flags == {"accepting_orders": False}
    assert "cancel_only" not in flags
    assert "delayed" not in flags


def test_clob_trading_flags_omit_missing_keys():
    assert clob_trading_flags({"question": "Will BTC hit 100k?"}) == {}
    assert clob_trading_flags(None) == {}
    assert "cancel_only" not in clob_trading_flags({"accepting_orders": True})
