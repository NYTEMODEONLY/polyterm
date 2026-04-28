"""Tests for live monitor fixed-dashboard rendering."""

from datetime import datetime, timezone

import pytest
from rich.console import Console

from polyterm.cli.commands.live_monitor import LiveMarketMonitor


def make_monitor(category="crypto"):
    """Create a LiveMarketMonitor without opening API clients or signal hooks."""
    monitor = LiveMarketMonitor.__new__(LiveMarketMonitor)
    monitor.market_id = None
    monitor.category = category
    monitor.console = Console(force_terminal=True)
    monitor._live_display = None
    monitor._ws_status = "connected"
    monitor._ws_reconnect_attempt = 0
    monitor._ws_max_reconnects = 5
    monitor.trade_count = 0
    monitor.total_volume = 0.0
    monitor.buy_count = 0
    monitor.sell_count = 0
    monitor.recent_trades = []
    monitor.max_recent_trades = 50
    monitor.status_messages = []
    monitor.max_status_messages = 4
    monitor.markets_count = 1
    monitor._last_trade_at = None
    monitor._dashboard_started_at = datetime(2026, 4, 28, 17, 30, tzinfo=timezone.utc)
    return monitor


def render_dashboard_text(monitor):
    """Render the dashboard to text for assertions."""
    console = Console(
        record=True,
        width=120,
        height=30,
        force_terminal=True,
        color_system=None,
    )
    console.print(monitor._render_live_dashboard())
    return console.export_text()


@pytest.mark.asyncio
async def test_live_dashboard_updates_header_metrics_and_recent_trades():
    monitor = make_monitor()
    trade = {
        "payload": {
            "eventSlug": "bitcoin-up-down",
            "slug": "bitcoin-up-down",
            "title": "Bitcoin Up or Down - April 28",
            "side": "BUY",
            "outcome": "Up",
            "size": "10",
            "price": "0.5",
        }
    }

    await monitor._handle_trade(trade, {"bitcoin-up-down": "Bitcoin Up or Down - April 28"})

    assert monitor.trade_count == 1
    assert monitor.buy_count == 1
    assert monitor.sell_count == 0
    assert monitor.total_volume == 5.0
    assert monitor.recent_trades[0]["market_title"] == "Bitcoin Up or Down - April 28"

    output = render_dashboard_text(monitor)

    assert "LIVE TRADE MONITOR" in output
    assert "Category: CRYPTO" in output
    assert "Trades: 1" in output
    assert "Volume: $5" in output
    assert "Bitcoin Up or Down - April 28" in output
    assert "BUY (Up)" in output


@pytest.mark.asyncio
async def test_live_dashboard_category_filter_skips_unmatched_trades():
    monitor = make_monitor(category="crypto")
    trade = {
        "payload": {
            "eventSlug": "nba-finals",
            "slug": "nba-finals",
            "title": "NBA Finals winner",
            "side": "SELL",
            "outcome": "No",
            "size": "10",
            "price": "0.5",
        }
    }

    await monitor._handle_trade(trade, {})

    assert monitor.trade_count == 0
    assert monitor.recent_trades == []

    output = render_dashboard_text(monitor)
    assert "Trades: 0" in output
    assert "Waiting for RTDS trades" in output


def test_live_dashboard_status_messages_are_capped():
    monitor = make_monitor()

    for index in range(6):
        monitor._add_status_message(f"message {index}", "cyan")

    assert len(monitor.status_messages) == 4
    assert monitor.status_messages[0]["message"] == "message 2"
    assert monitor.status_messages[-1]["message"] == "message 5"

    output = render_dashboard_text(monitor)
    assert "message 2" in output
    assert "message 5" in output
    assert "message 0" not in output
