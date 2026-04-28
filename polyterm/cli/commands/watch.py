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
from ...core.scanner import MarketScanner
from ...core.alerts import AlertManager


@click.command()
@click.option("--market", required=True, help="Market ID or search term")
@click.option("--threshold", default=10.0, help="Probability change threshold (%)")
@click.option("--volume-threshold", default=50.0, help="Volume change threshold (%)")
@click.option("--interval", default=60, help="Check interval in seconds")
@click.option("--notify", is_flag=True, help="Enable system notifications")
@click.pass_context
def watch(ctx, market, threshold, volume_threshold, interval, notify):
    """Watch specific markets with customizable alerts"""
    
    config = ctx.obj["config"]
    console = Console()
    
    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )
    # Find market
    console.print(f"[cyan]Searching for market: {market}[/cyan]")
    
    try:
        # Try as ID first
        market_data = gamma_client.get_market(market)
        market_id = market_data.get("id")
        market_title = market_data.get("question")
    except Exception:
        # Search by term
        results = gamma_client.search_markets(market, limit=5)
        if not results:
            console.print(f"[red]No markets found for: {market}[/red]")
            return
        
        # Show options
        console.print("\n[yellow]Multiple markets found:[/yellow]")
        for i, m in enumerate(results):
            console.print(f"  {i+1}. {m.get('question')}")
        
        choice = click.prompt("Select market number", type=int, default=1)
        selected = results[choice - 1]
        market_id = selected.get("id")
        market_title = selected.get("question")
    
    console.print(f"\n[green]Watching:[/green] {market_title}")
    console.print(f"[cyan]Probability threshold:[/cyan] {threshold}%")
    console.print(f"[cyan]Volume threshold:[/cyan] {volume_threshold}%")
    console.print(f"[cyan]Check interval:[/cyan] {interval}s\n")
    
    # Initialize scanner and alerts
    scanner = MarketScanner(
        gamma_client,
        clob_client,
        check_interval=interval,
    )
    
    alert_manager = AlertManager(
        enable_system_notifications=notify,
        enable_terminal_output=False,
    )
    
    # Add alert callback
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
        gamma_client.close()
        clob_client.close()


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
) -> Layout:
    """Render the fixed watch dashboard."""
    snapshots = scanner.snapshots.get(market_id, [])
    current = snapshots[-1] if snapshots else None
    previous = snapshots[-2] if len(snapshots) >= 2 else None
    changes = current.calculate_shift(previous) if current and previous else None

    header = Panel(
        Text.from_markup(
            "[bold green]Market Watch Active[/bold green]\n"
            f"[cyan]{market_title}[/cyan]\n"
            f"Checks: [cyan]{check_count}[/cyan] | Last check: [white]{last_check}[/white] | "
            f"Interval: [white]{interval}s[/white] | Notifications: [white]{'on' if notify else 'off'}[/white]\n"
            f"Probability threshold: [white]{threshold:.1f}%[/white] | "
            f"Volume threshold: [white]{volume_threshold:.1f}%[/white] | "
            "[dim]Press Ctrl+C to stop[/dim]"
        ),
        border_style="green",
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
    else:
        metrics.add_row("Status", "Waiting for first snapshot", Text("--", style="dim"))

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
        Layout(header, size=8),
        Layout(metrics, ratio=1),
        Layout(alerts, ratio=1),
    )
    return layout


def _format_change(value: float, suffix: str = "") -> Text:
    """Format a numeric change for dashboard tables."""
    if value > 0:
        return Text(f"+{value:.2f}{suffix}", style="green")
    if value < 0:
        return Text(f"{value:.2f}{suffix}", style="red")
    return Text(f"{value:.2f}{suffix}", style="yellow")
