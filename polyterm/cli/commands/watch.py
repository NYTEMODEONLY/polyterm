"""Watch command - monitor specific markets with alerts"""

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
from ...core.alert_engine import AlertEngine
from ...core.scanner import MarketScanner
from ...core.alerts import AlertManager
from ...core.service_health import ServiceHealth, assess_service_health, clob_trading_flags
from ...utils.json_output import print_json


@click.command()
@click.option("--market", required=True, help="Market ID or search term")
@click.option("--threshold", default=10.0, help="Probability change threshold (%)")
@click.option("--volume-threshold", default=50.0, help="Volume change threshold (%)")
@click.option("--interval", default=60, help="Check interval in seconds")
@click.option("--schedule", default=None, help="Run scheduled foreground scans, e.g. 15m")
@click.option("--runs", default=1, help="Number of scheduled scans in JSON/scheduled mode")
@click.option("--notify", default=None, help="Notification channel label, e.g. telegram or discord")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def watch(ctx, market, threshold, volume_threshold, interval, schedule, runs, notify, output_format):
    """Watch specific markets with customizable alerts.

    When Gamma and CLOB both fail, watch reports an outage instead of an
    empty market list. Unreachable status.polymarket.com is status_unknown,
    never operational.
    """

    config = ctx.obj["config"]
    console = Console()
    gamma_client, clob_client, status_client = _build_clients(config)

    try:
        if schedule or output_format == "json":
            _run_scheduled_watch(
                console=console,
                gamma_client=gamma_client,
                clob_client=clob_client,
                status_client=status_client,
                market=market,
                schedule=schedule,
                runs=runs,
                notify=notify,
                output_format=output_format,
                interval=interval,
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

        console.print(f"\n[green]Watching:[/green] {market_title}")
        console.print(f"[cyan]Probability threshold:[/cyan] {threshold}%")
        console.print(f"[cyan]Volume threshold:[/cyan] {volume_threshold}%")
        console.print(f"[cyan]Check interval:[/cyan] {interval}s")
        _print_health_line(console, health)
        console.print()

        scanner = MarketScanner(
            gamma_client,
            clob_client,
            check_interval=interval,
        )

        alert_manager = AlertManager(
            enable_system_notifications=notify,
            enable_terminal_output=False,
        )

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
            )

        try:
            scanner.running = True
            with Live(
                render_dashboard(),
                console=console,
                refresh_per_second=1,
                screen=True,
            ) as live:
                while scanner.running:
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

                    for shift in shifts:
                        recent_alerts.insert(0, {
                            "time": last_check,
                            "title": shift.get("title") or market_title,
                            "types": ", ".join(shift.get("shift_type", [])),
                        })
                    recent_alerts = recent_alerts[:8]

                    live.update(render_dashboard())
                    time.sleep(interval)
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopped watching market[/yellow]")
        finally:
            scanner.stop_monitoring()
    finally:
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
    market,
    schedule,
    runs,
    notify,
    output_format,
    interval,
):
    """JSON/scheduled scans. Outages are reported, never empty success."""
    engine = AlertEngine()
    delay = _parse_schedule(schedule) if schedule else interval
    results = []
    last_health = None
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
    )
    if output_format == "json":
        print_json(payload)
    else:
        _print_health_console(console, last_health, payload=payload)


def _scheduled_payload(market, schedule, notify, results, health):
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
) -> Layout:
    """Render the fixed watch dashboard."""
    snapshots = scanner.snapshots.get(market_id, [])
    current = snapshots[-1] if snapshots else None
    previous = snapshots[-2] if len(snapshots) >= 2 else None
    changes = current.calculate_shift(previous) if current and previous else None
    trading_flags = trading_flags or {}

    title_markup, border_style = _dashboard_title(health)
    health_line = _dashboard_health_line(health)
    flags_line = _dashboard_flags_line(trading_flags)

    header = Panel(
        Text.from_markup(
            f"{title_markup}\n"
            f"[cyan]{market_title}[/cyan]\n"
            f"Checks: [cyan]{check_count}[/cyan] | Last check: [white]{last_check}[/white] | "
            f"Interval: [white]{interval}s[/white] | Notifications: [white]{'on' if notify else 'off'}[/white]\n"
            f"Probability threshold: [white]{threshold:.1f}%[/white] | "
            f"Volume threshold: [white]{volume_threshold:.1f}%[/white] | "
            "[dim]Press Ctrl+C to stop[/dim]\n"
            f"{health_line}"
            f"{flags_line}"
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
        Layout(header, size=10),
        Layout(metrics, ratio=1),
        Layout(alerts, ratio=1),
    )
    return layout


def _dashboard_title(health: ServiceHealth = None):
    if health is None:
        return "[bold green]Market Watch Active[/bold green]", "green"
    if health.mode == "outage":
        return "[bold red]Market Watch Outage[/bold red]", "red"
    if health.mode == "degraded":
        return "[bold yellow]Market Watch Degraded[/bold yellow]", "yellow"
    if health.mode == "status_unknown":
        return "[bold yellow]Market Watch (status unknown)[/bold yellow]", "yellow"
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
