"""Market History - CLOB price history (refuses instead of inventing a path)"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.clob import CLOBClient
from ...api.gamma import GammaClient
from ...api.market_utils import get_primary_clob_token_id, market_probability_price
from ...core.price_history import (
    DEMO_DISCLOSURE,
    HISTORY_UNAVAILABLE,
    MISSING_TOKEN_IDS,
    SOURCE_DEMO,
    build_clob_payload,
    build_demo_payload,
    build_time_bounds,
    parse_clob_history_rows,
    period_to_hours,
    refuse_payload,
    select_clob_granularity,
)
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=True)
@click.option("--period", "-p", type=click.Choice(["day", "week", "month", "all"]), default="week", help="History period")
@click.option("--chart", "-c", is_flag=True, help="Show ASCII price chart (table mode always includes it)")
@click.option("--demo", is_flag=True, help="Show a labeled random-walk series instead of CLOB history")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def history(ctx, market_search, period, chart, demo, output_format):
    """View CLOB market price history

    Default path fetches YES prices from CLOB GET /prices-history.
    If that series is missing, the command refuses instead of inventing
    a random walk. Pass --demo for a labeled synthetic series.

    Examples:
        polyterm history "bitcoin"
        polyterm history "trump" --period month
        polyterm history "election" --demo
    """
    console = Console()
    config = ctx.obj["config"]

    if demo and output_format != "json":
        console.print()
        console.print(Panel(f"[yellow]{DEMO_DISCLOSURE}[/yellow]", border_style="yellow"))
        console.print()

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = None

    try:
        if output_format != "json":
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Loading history...", total=None)
                markets = gamma_client.search_markets(market_search, limit=1)
        else:
            markets = gamma_client.search_markets(market_search, limit=1)

        if not markets:
            payload = refuse_payload("Market not found", hint="search for an active Gamma market")
            _emit_payload(console, payload, output_format)
            return

        market = markets[0]
        title = market.get("question", market.get("title", "")) or market_search
        current_price = market_probability_price(market)
        volume_24h = _as_float(market.get("volume24hr", market.get("volume24h", 0)))
        reported_volume = _as_float(market.get("volume", 0))
        gamma_market_id = str(market.get("id") or "") or None

        if demo:
            payload = build_demo_payload(
                market_title=title,
                period=period,
                current_price=current_price or 0.5,
                volume_24h=volume_24h,
                reported_volume=reported_volume,
                seed_key=f"{market_search}:{period}",
                gamma_market_id=gamma_market_id,
            )
            _emit_payload(console, payload, output_format, show_chart=True)
            return

        token_id = get_primary_clob_token_id(market)
        if not token_id:
            _emit_payload(console, refuse_payload(MISSING_TOKEN_IDS), output_format)
            return

        hours = period_to_hours(period)
        interval, fidelity = select_clob_granularity(hours)
        start_ts, end_ts = build_time_bounds(hours)

        clob_client = CLOBClient(rest_endpoint=config.clob_rest_endpoint)
        try:
            raw_history = clob_client.get_price_history(
                token_id,
                interval=interval,
                fidelity=fidelity,
                start_ts=start_ts,
                end_ts=end_ts,
            )
        except Exception:
            _emit_payload(console, refuse_payload(HISTORY_UNAVAILABLE), output_format)
            return

        points = parse_clob_history_rows(raw_history, start_ts, end_ts)
        if not points:
            _emit_payload(console, refuse_payload(HISTORY_UNAVAILABLE), output_format)
            return

        payload = build_clob_payload(
            points,
            market_title=title,
            period=period,
            hours=hours,
            token_id=token_id,
            current_price=points[-1]["price"],
            volume_24h=volume_24h,
            reported_volume=reported_volume,
            gamma_market_id=gamma_market_id,
        )
        _emit_payload(console, payload, output_format, show_chart=True)
    finally:
        gamma_client.close()
        if clob_client is not None:
            clob_client.close()


def _emit_payload(console: Console, payload: dict, output_format: str, show_chart: bool = False) -> None:
    if output_format == "json":
        print_json(payload)
        return

    if not payload.get("success"):
        console.print()
        console.print(Panel(f"[yellow]{payload.get('error', 'History unavailable')}[/yellow]", border_style="yellow"))
        hint = payload.get("hint")
        if hint:
            console.print(f"[dim]Hint: {hint}[/dim]")
        console.print()
        return

    _render_history(console, payload, show_chart=show_chart)


def _render_history(console: Console, payload: dict, show_chart: bool) -> None:
    history_data = payload["history"]
    title = payload.get("market", "")
    source = payload.get("source")
    uses_historical = payload.get("uses_historical_data")

    console.print()
    if source == SOURCE_DEMO:
        header = f"[bold yellow]DEMO Price Path[/bold yellow]\n{title[:60]}\n[dim]{DEMO_DISCLOSURE}[/dim]"
        border = "yellow"
    else:
        token_id = payload.get("clob_token_id") or ""
        header = (
            f"[bold]CLOB Price History[/bold]\n{title[:60]}\n"
            f"[dim]Source: CLOB GET /prices-history"
            f"{f' (token {token_id[:16]}…)' if token_id else ''}"
        )
        border = "cyan"
    console.print(Panel(header, border_style=border))
    console.print()
    console.print(
        f"[dim]uses_historical_data={str(bool(uses_historical)).lower()}  "
        f"source={source}  period={payload.get('period')}  "
        f"points={payload.get('point_count', 0)}[/dim]"
    )
    console.print()

    current = history_data["current"]
    console.print(f"[bold]Current:[/bold] {current['price']:.1%}")
    console.print()

    console.print("[bold]Period Summary:[/bold]")
    console.print()

    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column(width=22)
    summary_table.add_column(justify="right", width=28)

    summary = history_data["summary"]
    change = summary["price_change"]
    change_color = "green" if change >= 0 else "red"
    summary_table.add_row("Price Change", f"[{change_color}]{change:+.1%}[/{change_color}]")
    summary_table.add_row("Period High", f"[green]{summary['high']:.1%}[/green]")
    summary_table.add_row("Period Low", f"[red]{summary['low']:.1%}[/red]")

    vol_str = f"{summary['volatility']:.1%}"
    if summary["volatility"] > 0.15:
        vol_str = f"[red]{vol_str}[/red] (High)"
    elif summary["volatility"] > 0.05:
        vol_str = f"[yellow]{vol_str}[/yellow] (Normal)"
    else:
        vol_str = f"[green]{vol_str}[/green] (Low)"
    summary_table.add_row("Volatility", vol_str)
    summary_table.add_row(
        "Reported volume",
        f"${summary.get('reported_volume', 0):,.0f} [dim](Gamma snapshot)[/dim]",
    )
    console.print(summary_table)
    console.print()

    if show_chart:
        label = "DEMO Price Path:" if source == SOURCE_DEMO else "Price History:"
        console.print(f"[bold]{label}[/bold]")
        console.print()
        _display_chart(console, history_data["points"])
        console.print()

    if history_data.get("milestones"):
        console.print("[bold]Key Moments:[/bold]")
        console.print()
        for milestone in history_data["milestones"][:5]:
            if milestone["type"] == "high":
                icon = "[green]↑[/green]"
            elif milestone["type"] == "low":
                icon = "[red]↓[/red]"
            else:
                icon = "[yellow]•[/yellow]"
            console.print(f"  {icon} {milestone['date']}: {milestone['description']}")
        console.print()

    console.print("[bold]Trend:[/bold]")
    trend = history_data["trend"]
    if trend["direction"] == "up":
        console.print(f"[green]Uptrend[/green] - Price rising {trend['strength']}")
    elif trend["direction"] == "down":
        console.print(f"[red]Downtrend[/red] - Price falling {trend['strength']}")
    else:
        console.print("[yellow]Sideways[/yellow] - Consolidating in range")
    console.print()


def _display_chart(console: Console, points: list) -> None:
    """Display ASCII price chart from series points."""
    if not points:
        console.print("[dim]No data[/dim]")
        return

    prices = [point["price"] for point in points]
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price or 0.01
    height = 8
    width = min(len(points), 40)

    if len(points) > width:
        step = len(points) / width
        sampled = [points[int(i * step)] for i in range(width)]
    else:
        sampled = points

    chart = []
    for row in range(height, -1, -1):
        line = ""
        threshold = min_price + (row / height) * price_range
        for point in sampled:
            line += "█" if point["price"] >= threshold else " "
        if row == height:
            chart.append(f"  {max_price:.0%} │{line}│")
        elif row == 0:
            chart.append(f"  {min_price:.0%} │{line}│")
        elif row == height // 2:
            mid = (min_price + max_price) / 2
            chart.append(f"  {mid:.0%} │{line}│")
        else:
            chart.append(f"       │{line}│")

    if sampled:
        first_date = sampled[0]["date"]
        last_date = sampled[-1]["date"]
        date_line = f"       {first_date}" + " " * (len(sampled) - len(first_date) - len(last_date)) + last_date
        chart.append("       └" + "─" * len(sampled) + "┘")
        chart.append(date_line)

    for line in chart:
        console.print(f"[cyan]{line}[/cyan]")


def _as_float(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0
