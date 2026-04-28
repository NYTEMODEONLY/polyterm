"""Tests for fixed live-screen rendering conventions."""

import ast
from pathlib import Path

from rich.console import Console

from polyterm.cli.commands.watch import _render_watch_dashboard
from polyterm.cli.commands.watchdog import _render_watchdog_dashboard
from polyterm.core.alerts import Alert, AlertLevel, AlertManager
from polyterm.core.scanner import MarketSnapshot


REPO_ROOT = Path(__file__).resolve().parents[2]

LIVE_SURFACE_FILES = [
    "polyterm/cli/commands/arbitrage.py",
    "polyterm/cli/commands/crypto15m.py",
    "polyterm/cli/commands/live_monitor.py",
    "polyterm/cli/commands/monitor.py",
    "polyterm/cli/commands/orderbook.py",
    "polyterm/cli/commands/watch.py",
    "polyterm/cli/commands/watchdog.py",
    "polyterm/tui/screens/orderbook_screen.py",
]


def render_text(renderable):
    """Render a Rich object to plain text for assertions."""
    console = Console(
        record=True,
        width=120,
        height=32,
        force_terminal=True,
        color_system=None,
    )
    console.print(renderable)
    return console.export_text()


def live_calls_in(path):
    """Return every Rich Live(...) call in a source file."""
    tree = ast.parse((REPO_ROOT / path).read_text())
    calls = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "Live":
            calls.append(node)
        elif isinstance(func, ast.Attribute) and func.attr == "Live":
            calls.append(node)
    return calls


def test_all_live_surfaces_use_fixed_screen_mode():
    """Continuously updating terminal surfaces should not push headers into scrollback."""
    for path in LIVE_SURFACE_FILES:
        calls = live_calls_in(path)
        assert calls, f"{path} has no Live(...) calls"
        for call in calls:
            screen_kw = next((kw for kw in call.keywords if kw.arg == "screen"), None)
            assert screen_kw is not None, f"{path} Live(...) missing screen=True"
            assert isinstance(screen_kw.value, ast.Constant), f"{path} screen is not static"
            assert screen_kw.value.value is True, f"{path} Live(...) must use screen=True"


def test_watch_dashboard_keeps_status_metrics_and_alerts_visible():
    """The watch command dashboard should render fixed status plus recent alerts."""
    scanner = type("FakeScanner", (), {})()
    scanner.snapshots = {
        "m1": [
            MarketSnapshot("m1", {
                "title": "Bitcoin Test Market",
                "probability": 50.0,
                "price": 0.50,
                "volume": 1000,
                "liquidity": 5000,
            }, 1.0),
            MarketSnapshot("m1", {
                "title": "Bitcoin Test Market",
                "probability": 57.0,
                "price": 0.57,
                "volume": 1500,
                "liquidity": 5200,
            }, 2.0),
        ]
    }

    output = render_text(_render_watch_dashboard(
        scanner=scanner,
        market_id="m1",
        market_title="Bitcoin Test Market",
        threshold=10.0,
        volume_threshold=50.0,
        interval=30,
        notify=False,
        check_count=3,
        last_check="12:30:00",
        recent_alerts=[{
            "time": "12:30:00",
            "title": "Bitcoin Test Market",
            "types": "probability",
        }],
    ))

    assert "Market Watch Active" in output
    assert "Checks: 3" in output
    assert "Bitcoin Test Market" in output
    assert "Probability" in output
    assert "Recent Alerts" in output
    assert "probability" in output


def test_watchdog_dashboard_keeps_status_market_state_and_alerts_visible():
    """The watchdog dashboard should render fixed status plus recent alerts."""
    output = render_text(_render_watchdog_dashboard(
        watched_markets=[{
            "title": "Ethereum Test Market",
            "initial_price": 0.40,
            "last_price": 0.45,
            "last_volume": 25000,
            "alerts": [{"time": "12:30:00", "alert": {"type": "above"}}],
        }],
        conditions=[{"type": "above", "value": 0.44}],
        interval=15,
        duration=5,
        start_time=0,
        check_count=4,
        last_check="12:30:00",
        recent_alerts=[{
            "time": "12:30:00",
            "market": "Ethereum Test Market",
            "alert": {"type": "above", "message": "Price crossed above 44%"},
        }],
    ))

    assert "Watchdog Active" in output
    assert "Checks: 4" in output
    assert "Ethereum Test Market" in output
    assert "Recent Alerts" in output
    assert "Price crossed above 44%" in output


def test_alert_manager_can_suppress_terminal_output(capsys):
    """Live dashboards can store/send alerts without writing into scrollback."""
    manager = AlertManager(enable_terminal_output=False)

    manager.dispatch_alert(Alert(
        market_id="m1",
        title="Bitcoin Test Market",
        message="Probability increased",
        level=AlertLevel.WARNING,
    ))

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert len(manager.alert_history) == 1
