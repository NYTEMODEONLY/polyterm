"""Watch command - one live session: CLOB book, lagged prints, outage line."""

import click
import time
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.layout import Layout
from rich.text import Text

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.status import StatusPageClient
from ...api.data_api_lag import DISCLOSURE, QUALITY_FLAG
from ...core.alert_engine import AlertEngine
from ...core.scanner import MarketScanner
from ...core.alerts import AlertManager
from ...core.print_scanner import PrintScanner
from ...core.service_health import ServiceHealth, assess_service_health, clob_trading_flags
from ...core.uma_tracker import resolution_dashboard_line, snapshot_market_resolution
from ...core.watch_loop import (
    DEFAULT_PRINT_MIN_NOTIONAL,
    WatchBookSession,
    collect_watch_surfaces,
    dispatch_watch_notifications,
    new_notify_state,
    notify_events_from_scan,
    token_ids_for_market,
    watch_notifier,
)
from ...core.ws_book_freshness import DEFAULT_STALE_AFTER_SECONDS, WS_STALE_BANNER
from ...utils.json_output import print_json


@click.command()
@click.option("--market", required=True, help="Market ID or search term")
@click.option("--threshold", default=10.0, help="Probability change threshold (%)")
@click.option("--volume-threshold", default=50.0, help="Volume change threshold (%)")
@click.option("--interval", default=60, help="Check interval in seconds")
@click.option("--schedule", default=None, help="Run scheduled foreground scans, e.g. 15m")
@click.option("--runs", default=1, help="Number of scheduled scans in JSON/scheduled mode")
@click.option(
    "--notify",
    default=None,
    help="telegram or discord: send only on verified prints and threshold events, not every poll",
)
@click.option(
    "--min-notional",
    default=DEFAULT_PRINT_MIN_NOTIONAL,
    type=float,
    help="Minimum lagged Data API print notional to notify on (default 10000; no saved print rule required)",
)
@click.option(
    "--stale-after",
    default=int(DEFAULT_STALE_AFTER_SECONDS),
    type=int,
    help="Seconds without book/price_change ticks before a connected CLOB WS is ws_stale (default 20)",
)
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def watch(
    ctx,
    market,
    threshold,
    volume_threshold,
    interval,
    schedule,
    runs,
    notify,
    min_notional,
    stale_after,
    output_format,
):
    """Watch one market: CLOB book, lagged prints, UMA/resolution, outage line.

    A connected WebSocket with no book/price_change ticks is not live
    (ws_stale / "WS connected, no book ticks"). Prints are lagged Data API
    fills, never a live CLOB tape. Resolution/UMA is copied from Gamma
    (disputed, proposed, hours remaining, open-for-trading vs redeemable).
    Missing UMA data is status=none, never a fairness grade. Telegram/Discord
    notify only on verified prints and price/volume threshold events, not
    every poll.
    """

    config = ctx.obj["config"]
    console = Console()
    gamma_client, clob_client, status_client = _build_clients(config)
    print_scanner = PrintScanner()
    book_session = None

    try:
        if schedule or output_format == "json":
            _run_scheduled_watch(
                console=console,
                gamma_client=gamma_client,
                clob_client=clob_client,
                status_client=status_client,
                print_scanner=print_scanner,
                config=config,
                market=market,
                schedule=schedule,
                runs=runs,
                notify=notify,
                output_format=output_format,
                interval=interval,
                min_notional=min_notional,
                stale_after=stale_after,
            )
            return

        health = assess_service_health(gamma_client, clob_client, status_client)
        if health.mode == "outage" or not health.gamma.ok:
            _print_health_console(console, health)
            return

        market_id, market_title, market_data = _resolve_watch_market(
            console, gamma_client, market
        )
        if not market_id:
            return

        trading_flags = clob_trading_flags(market_data)
        book_session = WatchBookSession(
            clob_client,
            token_ids_for_market(market_data),
            stale_after_seconds=stale_after,
        )
        book_session.start()
        book_payload = book_session.snapshot()
        prints_payload = {
            "prints": [],
            "count": 0,
            "quality_flags": [QUALITY_FLAG],
        }
        resolution_payload = snapshot_market_resolution(market_data)

        console.print(f"\n[green]Watching:[/green] {market_title}")
        console.print(f"[cyan]Probability threshold:[/cyan] {threshold}%")
        console.print(f"[cyan]Volume threshold:[/cyan] {volume_threshold}%")
        console.print(f"[cyan]Check interval:[/cyan] {interval}s")
        console.print(
            f"[cyan]Print min-notional:[/cyan] ${float(min_notional):,.0f} "
            "[dim](lagged Data API, not live CLOB)[/dim]"
        )
        console.print(
            f"[cyan]WS stale after:[/cyan] {stale_after}s without book ticks"
        )
        _print_health_line(console, health)
        console.print(f"[dim]{DISCLOSURE}[/dim]")
        console.print()

        scanner = MarketScanner(
            gamma_client,
            clob_client,
            check_interval=interval,
        )

        alert_manager = AlertManager(
            enable_system_notifications=bool(notify),
            enable_terminal_output=False,
        )
        notifier = watch_notifier(config, notify)
        notify_state = new_notify_state()

        def on_shift(shift_data):
            thresholds = {
                "probability": threshold,
                "volume": volume_threshold,
            }
            alert_manager.process_shift(shift_data, thresholds)

        scanner.add_shift_callback(on_shift)

        recent_alerts = []
        check_count = 0
        last_check = "waiting"

        def render_dashboard():
            return _render_watch_dashboard(
                scanner=scanner,
                market_id=market_id,
                market_title=market_title,
                threshold=threshold,
                volume_threshold=volume_threshold,
                interval=interval,
                notify=notify,
                check_count=check_count,
                last_check=last_check,
                recent_alerts=recent_alerts,
                health=health,
                trading_flags=trading_flags,
                prints_payload=prints_payload,
                book_payload=book_payload,
                resolution_payload=resolution_payload,
                min_notional=min_notional,
            )

        try:
            scanner.running = True
            next_scan = 0.0
            with Live(
                render_dashboard(),
                console=console,
                refresh_per_second=1,
                screen=True,
            ) as live:
                while scanner.running:
                    now = time.time()
                    if now >= next_scan:
                        check_count += 1
                        last_check = datetime.now().strftime("%H:%M:%S")
                        health = assess_service_health(
                            gamma_client, clob_client, status_client
                        )
                        shifts = []
                        if health.mode != "outage" and health.gamma.ok:
                            shifts = scanner.scan_markets(
                                market_ids=[market_id],
                                thresholds={
                                    "probability": threshold,
                                    "volume": volume_threshold,
                                },
                            )
                            surfaces = collect_watch_surfaces(
                                market=market,
                                gamma_client=gamma_client,
                                clob_client=None,
                                print_scanner=print_scanner,
                                market_data=market_data,
                                min_notional=min_notional,
                                stale_after_seconds=stale_after,
                            )
                            prints_payload = surfaces.get("prints") or prints_payload
                            if surfaces.get("resolution"):
                                resolution_payload = surfaces["resolution"]
                            events = notify_events_from_scan(
                                prints_payload,
                                shifts,
                                min_notional,
                                notify_state,
                            )
                            if notifier and events:
                                dispatch_watch_notifications(notify, events, notifier)

                        for shift in shifts:
                            recent_alerts.insert(0, {
                                "time": last_check,
                                "title": shift.get("title") or market_title,
                                "types": ", ".join(shift.get("shift_type", [])),
                            })
                        recent_alerts = recent_alerts[:8]
                        next_scan = now + max(int(interval), 1)

                    book_payload = book_session.snapshot()
                    live.update(render_dashboard())
                    time.sleep(1)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped watching market[/yellow]")
        finally:
            scanner.stop_monitoring()
    finally:
        if book_session is not None:
            try:
                book_session.stop()
            except Exception:
                pass
        _close_clients(gamma_client, clob_client, status_client)


def _build_clients(config):
    """Construct Gamma, CLOB, and status-page clients from config."""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )
    status_client = StatusPageClient()
    return gamma_client, clob_client, status_client


def _close_clients(*clients):
    for client in clients:
        closer = getattr(client, "close", None)
        if closer is None:
            continue
        try:
            closer()
        except Exception:
            pass


def _run_scheduled_watch(
    console,
    gamma_client,
    clob_client,
    status_client,
    print_scanner,
    config,
    market,
    schedule,
    runs,
    notify,
    output_format,
    interval,
    min_notional,
    stale_after,
):
    """JSON/scheduled scans. Outages are reported, never empty success."""
    engine = AlertEngine()
    delay = _parse_schedule(schedule) if schedule else interval
    results = []
    last_health = None
    notifier = watch_notifier(config, notify)
    notify_state = new_notify_state()
    try:
        for index in range(max(runs, 1)):
            last_health = assess_service_health(
                gamma_client, clob_client, status_client
            )
            if last_health.mode == "outage" or not last_health.gamma.ok:
                results.append({
                    "success": False,
                    "mode": last_health.mode,
                    "status": last_health.status,
                    "market": market,
                    "error": last_health.message,
                    "health": last_health.to_dict(),
                })
            else:
                scan = engine.run_once(market=market)
                scan["mode"] = last_health.mode
                scan["status"] = last_health.status
                scan["health"] = last_health.to_dict()
                surfaces = collect_watch_surfaces(
                    market=market,
                    gamma_client=gamma_client,
                    clob_client=clob_client,
                    print_scanner=print_scanner,
                    min_notional=min_notional,
                    stale_after_seconds=stale_after,
                )
                scan["prints"] = surfaces.get("prints")
                scan["book"] = surfaces.get("book")
                scan["resolution"] = surfaces.get("resolution")
                events = notify_events_from_scan(
                    surfaces.get("prints") or {},
                    None,
                    min_notional,
                    notify_state,
                )
                if notifier and events:
                    scan["notify_sent"] = dispatch_watch_notifications(
                        notify, events, notifier
                    )
                elif notify:
                    scan["notify_sent"] = []
                results.append(scan)
            if schedule and index < runs - 1:
                time.sleep(delay)
    except KeyboardInterrupt:
        pass

    payload = _scheduled_payload(
        market=market,
        schedule=schedule,
        notify=notify,
        results=results,
        health=last_health,
        min_notional=min_notional,
        stale_after=stale_after,
    )
    if output_format == "json":
        print_json(payload)
    else:
        _print_health_console(console, last_health, payload=payload)


def _scheduled_payload(
    market,
    schedule,
    notify,
    results,
    health,
    min_notional=DEFAULT_PRINT_MIN_NOTIONAL,
    stale_after=DEFAULT_STALE_AFTER_SECONDS,
):
    """Build the scheduled-watch JSON object with honest outage fields."""
    mode = health.mode if health is not None else "status_unknown"
    status = health.status if health is not None else "status_unknown"
    if any(item.get("mode") == "outage" for item in results):
        mode = "outage"
        status = "outage"
    elif mode != "outage" and any(item.get("status") == "degraded" for item in results):
        if mode == "operational":
            mode = "degraded"
            status = "degraded"

    success = mode != "outage" and all(
        item.get("success", True) is not False for item in results
    )
    payload = {
        "success": success,
        "mode": mode,
        "status": status,
        "market": market,
        "schedule": schedule,
        "runs": len(results),
        "notify": notify,
        "min_notional": min_notional,
        "stale_after": stale_after,
        "results": results,
        "long_running": bool(schedule),
    }
    if health is not None:
        payload["health"] = health.to_dict()
        payload["error"] = None if success else health.message
    return payload


def _resolve_watch_market(console, gamma_client, market):
    """Resolve a watch target via Gamma. Empty search is not an outage."""
    console.print(f"[cyan]Searching for market: {market}[/cyan]")

    try:
        market_data = gamma_client.get_market(market)
        market_id = market_data.get("id")
        market_title = market_data.get("question")
        if market_id:
            return market_id, market_title, market_data
    except Exception:
        pass

    results = gamma_client.search_markets(market, limit=5)
    if not results:
        console.print(f"[red]No markets found for: {market}[/red]")
        return None, None, None

    console.print("\n[yellow]Multiple markets found:[/yellow]")
    for i, item in enumerate(results):
        console.print(f"  {i+1}. {item.get('question')}")

    choice = click.prompt("Select market number", type=int, default=1)
    selected = results[choice - 1]
    return selected.get("id"), selected.get("question"), selected


def _print_health_line(console, health: ServiceHealth):
    color = {
        "operational": "green",
        "degraded": "yellow",
        "outage": "red",
        "status_unknown": "yellow",
    }.get(health.mode, "yellow")
    console.print(
        f"[{color}]API {health.mode}[/{color}]: {health.message}"
    )


def _print_health_console(console, health, payload=None):
    """Human-readable outage/degraded report for table mode."""
    if health is None:
        console.print("[red]Watch could not assess API health.[/red]")
        return
    if health.mode == "outage":
        console.print(f"[red]Watch outage:[/red] {health.message}")
        console.print(
            "[dim]Gamma and CLOB both failed. This is an outage, not an empty market list.[/dim]"
        )
    elif health.mode == "degraded":
        console.print(f"[yellow]Watch degraded:[/yellow] {health.message}")
    elif health.mode == "status_unknown":
        console.print(
            f"[yellow]Status page unknown:[/yellow] {health.message}"
        )
        console.print("[dim]status.polymarket.com did not confirm operational.[/dim]")
    else:
        console.print(f"[green]Watch {health.mode}:[/green] {health.message}")
    if payload is not None:
        console.print(
            f"[cyan]Completed {payload.get('runs', 0)} scheduled scan(s).[/cyan]"
        )


def _render_watch_dashboard(
    scanner: MarketScanner,
    market_id: str,
    market_title: str,
    threshold: float,
    volume_threshold: float,
    interval: int,
    notify: bool,
    check_count: int,
    last_check: str,
    recent_alerts: list,
    health: ServiceHealth = None,
    trading_flags: dict = None,
    prints_payload: dict = None,
    book_payload: dict = None,
    resolution_payload: dict = None,
    min_notional: float = DEFAULT_PRINT_MIN_NOTIONAL,
) -> Layout:
    """Render the fixed watch dashboard."""
    snapshots = scanner.snapshots.get(market_id, [])
    current = snapshots[-1] if snapshots else None
    previous = snapshots[-2] if len(snapshots) >= 2 else None
    changes = current.calculate_shift(previous) if current and previous else None
    trading_flags = trading_flags or {}
    book_payload = book_payload or {}
    prints_payload = prints_payload or {}
    resolution_payload = resolution_payload or {}

    title_markup, border_style = _dashboard_title(health, book_payload)
    health_line = _dashboard_health_line(health)
    flags_line = _dashboard_flags_line(trading_flags)
    book_line = _dashboard_book_line(book_payload)
    resolution_line = _dashboard_resolution_line(resolution_payload)

    header = Panel(
        Text.from_markup(
            f"{title_markup}\n"
            f"[cyan]{market_title}[/cyan]\n"
            f"Checks: [cyan]{check_count}[/cyan] | Last check: [white]{last_check}[/white] | "
            f"Interval: [white]{interval}s[/white] | Notifications: [white]{'on' if notify else 'off'}[/white]\n"
            f"Probability threshold: [white]{threshold:.1f}%[/white] | "
            f"Volume threshold: [white]{volume_threshold:.1f}%[/white] | "
            f"Print min-notional: [white]${float(min_notional):,.0f}[/white] | "
            "[dim]Press Ctrl+C to stop[/dim]\n"
            f"{health_line}"
            f"{flags_line}"
            f"{book_line}"
            f"{resolution_line}"
        ),
        border_style=border_style,
        padding=(0, 2),
    )

    metrics = Table(title="Current Market State", title_style="bold cyan", expand=True)
    metrics.add_column("Metric", style="cyan", width=18)
    metrics.add_column("Value", justify="right", style="white")
    metrics.add_column("Change", justify="right")

    if current:
        probability = float(current.probability or 0)
        volume = float(current.volume or 0)
        liquidity = float(current.liquidity or 0)
        price = float(current.price or 0)
        prob_change = changes["probability_change"] if changes else 0
        volume_change = changes["volume_change"] if changes else 0
        liquidity_change = changes["liquidity_change"] if changes else 0
        price_change = changes["price_change"] if changes else 0

        metrics.add_row("Probability", f"{probability:.1f}%", _format_change(prob_change, "%"))
        metrics.add_row("Price", f"${price:.4f}", _format_change(price_change, "%"))
        metrics.add_row("Volume", f"${volume:,.0f}", _format_change(volume_change, "%"))
        metrics.add_row("Liquidity", f"${liquidity:,.0f}", _format_change(liquidity_change, "%"))
    elif health is not None and health.mode == "outage":
        metrics.add_row(
            "Status",
            "Gamma and CLOB both failed",
            Text("outage", style="red"),
        )
    elif health is not None and health.mode == "degraded":
        metrics.add_row(
            "Status",
            health.message,
            Text("degraded", style="yellow"),
        )
    else:
        metrics.add_row("Status", "Waiting for first snapshot", Text("--", style="dim"))

    if "accepting_orders" in trading_flags:
        accepting = trading_flags["accepting_orders"]
        metrics.add_row(
            "accepting_orders",
            str(accepting),
            Text("clob", style="dim"),
        )

    if book_payload.get("best_bid") is not None or book_payload.get("best_ask") is not None:
        bid = book_payload.get("best_bid")
        ask = book_payload.get("best_ask")
        metrics.add_row(
            "Book",
            f"{_fmt_px(bid)} / {_fmt_px(ask)}",
            Text(str(book_payload.get("source") or ""), style="dim"),
        )

    prints_table = _render_prints_table(prints_payload)
    alerts = Table(title="Recent Alerts", title_style="bold yellow", expand=True)
    alerts.add_column("Time", style="dim", width=8)
    alerts.add_column("Market", style="white", ratio=1, overflow="ellipsis")
    alerts.add_column("Type", style="yellow", width=20)

    if recent_alerts:
        for alert in recent_alerts:
            alerts.add_row(alert["time"], alert["title"], alert["types"])
    else:
        alerts.add_row("--:--:--", "No shifts detected yet", Text("waiting", style="dim"))

    layout = Layout()
    layout.split_column(
        Layout(header, size=13),
        Layout(metrics, ratio=1),
        Layout(prints_table, ratio=1),
        Layout(alerts, ratio=1),
    )
    return layout


def _fmt_px(value):
    if value is None:
        return "—"
    try:
        return f"${float(value):.4f}"
    except (TypeError, ValueError):
        return "—"


def _render_prints_table(prints_payload: dict) -> Table:
    """Recent lagged Data API prints. Empty tape is empty, not synthetic."""
    table = Table(
        title="Lagged Data API prints (not live CLOB)",
        title_style="bold magenta",
        expand=True,
    )
    table.add_column("When", style="dim", width=12)
    table.add_column("Side", width=6)
    table.add_column("Notional", justify="right", width=12)
    table.add_column("Wallet", style="white", ratio=1, overflow="ellipsis")

    rows = []
    if isinstance(prints_payload, dict):
        rows = [row for row in (prints_payload.get("prints") or []) if isinstance(row, dict)]

    if not rows:
        table.add_row("--", "—", "—", Text("No lagged Data API prints", style="dim"))
        return table

    for row in rows[:8]:
        when = row.get("timestamp_iso") or row.get("timestamp") or "—"
        if isinstance(when, (int, float)):
            when = str(when)
        side = str(row.get("side") or "—")
        notional = row.get("notional")
        if notional is None:
            notional_text = "unknown"
        else:
            try:
                notional_text = f"${float(notional):,.0f}"
            except (TypeError, ValueError):
                notional_text = "unknown"
        wallet = str(row.get("wallet") or "unknown")
        table.add_row(str(when)[:19], side, notional_text, wallet)
    return table


def _dashboard_title(health: ServiceHealth = None, book_payload: dict = None):
    book_payload = book_payload or {}
    if book_payload.get("ws_stale"):
        return "[bold yellow]Market Watch (WS stale)[/bold yellow]", "yellow"
    if health is None:
        return "[bold green]Market Watch Active[/bold green]", "green"
    if health.mode == "outage":
        return "[bold red]Market Watch Outage[/bold red]", "red"
    if health.mode == "degraded":
        return "[bold yellow]Market Watch Degraded[/bold yellow]", "yellow"
    if health.mode == "status_unknown":
        return "[bold yellow]Market Watch (status unknown)[/bold yellow]", "yellow"
    if book_payload.get("live"):
        return "[bold green]Market Watch Active[/bold green]", "green"
    if book_payload.get("source") == "clob_rest":
        return "[bold cyan]Market Watch (CLOB REST snapshot)[/bold cyan]", "cyan"
    return "[bold green]Market Watch Active[/bold green]", "green"


def _dashboard_health_line(health: ServiceHealth = None) -> str:
    if health is None:
        return "[dim]API health: not assessed[/dim]"
    gamma = "ok" if health.gamma.ok else "fail"
    clob = "ok" if health.clob.ok else "fail"
    page = health.status_page.indicator
    return (
        f"API: [white]{health.mode}[/white] | "
        f"Gamma: [white]{gamma}[/white] | "
        f"CLOB: [white]{clob}[/white] | "
        f"Status page: [white]{page}[/white]"
    )


def _dashboard_flags_line(trading_flags: dict) -> str:
    if "accepting_orders" not in trading_flags:
        return ""
    return f"\naccepting_orders: [white]{trading_flags['accepting_orders']}[/white]"


def _dashboard_book_line(book_payload: dict) -> str:
    if not book_payload:
        return ""
    source = book_payload.get("source") or "none"
    if book_payload.get("ws_stale"):
        banner = book_payload.get("banner") or WS_STALE_BANNER
        return (
            f"\nBook: [yellow]{banner}[/yellow] | "
            f"source=[white]{source}[/white] | live=[white]false[/white]"
        )
    live = "true" if book_payload.get("live") else "false"
    return (
        f"\nBook source: [white]{source}[/white] | live=[white]{live}[/white]"
    )


def _dashboard_resolution_line(resolution_payload: dict) -> str:
    line = resolution_dashboard_line(resolution_payload)
    if not line:
        return ""
    status = str(resolution_payload.get("status") or "none")
    color = {
        "disputed": "yellow",
        "proposed": "yellow",
        "pending": "yellow",
        "resolved": "green",
        "none": "dim",
    }.get(status, "white")
    return f"\n[{color}]{line}[/{color}]"


def _format_change(value: float, suffix: str = "") -> Text:
    """Format a numeric change for dashboard tables."""
    if value > 0:
        return Text(f"+{value:.2f}{suffix}", style="green")
    if value < 0:
        return Text(f"{value:.2f}{suffix}", style="red")
    return Text(f"{value:.2f}{suffix}", style="yellow")


def _parse_schedule(value: str) -> int:
    """Parse schedule values such as 15m, 1h, or 30s."""
    value = str(value).strip().lower()
    if value.endswith("m"):
        return int(float(value[:-1]) * 60)
    if value.endswith("h"):
        return int(float(value[:-1]) * 3600)
    if value.endswith("s"):
        return int(float(value[:-1]))
    return int(float(value))
