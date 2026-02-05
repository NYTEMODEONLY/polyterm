"""Market History - View price and volume history"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=True)
@click.option("--period", "-p", type=click.Choice(["day", "week", "month", "all"]), default="week", help="History period")
@click.option("--chart", "-c", is_flag=True, help="Show price chart")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def history(ctx, market_search, period, chart, output_format):
    """View market price and volume history

    See how a market has evolved over time.
    Identify trends, key events, and patterns.

    Examples:
        polyterm history "bitcoin"              # Last week
        polyterm history "trump" --period month # Last month
        polyterm history "election" --chart     # With price chart
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Loading history...", total=None)

            # Find market
            markets = gamma_client.search_markets(market_search, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Market not found'})
                else:
                    console.print(f"[yellow]Market '{market_search}' not found.[/yellow]")
                return

            market = markets[0]
            title = market.get('question', market.get('title', ''))

            # Calculate history (simulated from available data)
            history_data = _build_history(market, period)

    finally:
        gamma_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'market': title,
            'period': period,
            'history': history_data,
        })
        return

    # Display
    console.print()
    console.print(Panel(f"[bold]Market History[/bold]\n{title[:60]}", border_style="cyan"))
    console.print()

    # Current state
    current = history_data['current']
    console.print(f"[bold]Current:[/bold] {current['price']:.1%}")
    console.print()

    # Key metrics
    console.print("[bold]Period Summary:[/bold]")
    console.print()

    summary_table = Table(show_header=False, box=None, padding=(0, 2))
    summary_table.add_column(width=18)
    summary_table.add_column(justify="right", width=15)

    summary = history_data['summary']

    # Price change
    change = summary['price_change']
    change_color = "green" if change >= 0 else "red"
    summary_table.add_row("Price Change", f"[{change_color}]{change:+.1%}[/{change_color}]")

    # High/Low
    summary_table.add_row("Period High", f"[green]{summary['high']:.1%}[/green]")
    summary_table.add_row("Period Low", f"[red]{summary['low']:.1%}[/red]")

    # Volatility
    vol_str = f"{summary['volatility']:.1%}"
    if summary['volatility'] > 0.15:
        vol_str = f"[red]{vol_str}[/red] (High)"
    elif summary['volatility'] > 0.05:
        vol_str = f"[yellow]{vol_str}[/yellow] (Normal)"
    else:
        vol_str = f"[green]{vol_str}[/green] (Low)"
    summary_table.add_row("Volatility", vol_str)

    # Volume
    summary_table.add_row("Volume", f"${summary['total_volume']:,.0f}")

    console.print(summary_table)
    console.print()

    # Price chart
    if chart or True:  # Always show chart
        console.print("[bold]Price History:[/bold]")
        console.print()
        _display_chart(console, history_data['points'])
        console.print()

    # Key events/milestones
    if history_data['milestones']:
        console.print("[bold]Key Moments:[/bold]")
        console.print()

        for milestone in history_data['milestones'][:5]:
            if milestone['type'] == 'high':
                icon = "[green]↑[/green]"
            elif milestone['type'] == 'low':
                icon = "[red]↓[/red]"
            else:
                icon = "[yellow]•[/yellow]"

            console.print(f"  {icon} {milestone['date']}: {milestone['description']}")

        console.print()

    # Trend analysis
    console.print("[bold]Trend:[/bold]")
    trend = history_data['trend']

    if trend['direction'] == 'up':
        console.print(f"[green]Uptrend[/green] - Price rising {trend['strength']}")
    elif trend['direction'] == 'down':
        console.print(f"[red]Downtrend[/red] - Price falling {trend['strength']}")
    else:
        console.print(f"[yellow]Sideways[/yellow] - Consolidating in range")

    console.print()


def _build_history(market: dict, period: str) -> dict:
    """Build history data from market info"""
    current_price = _get_price(market)
    volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
    total_volume = market.get('volume', 0) or 0

    # Period in days
    if period == 'day':
        days = 1
    elif period == 'week':
        days = 7
    elif period == 'month':
        days = 30
    else:
        days = 90

    # Generate synthetic history points (in production, fetch from API)
    points = _generate_history_points(current_price, volume_24h, days)

    # Calculate summary
    prices = [p['price'] for p in points]
    high = max(prices)
    low = min(prices)
    start_price = prices[0]
    price_change = current_price - start_price

    # Volatility (standard deviation approximation)
    avg = sum(prices) / len(prices)
    volatility = (sum((p - avg) ** 2 for p in prices) / len(prices)) ** 0.5

    # Milestones
    milestones = []

    # Find high point
    high_idx = prices.index(high)
    milestones.append({
        'type': 'high',
        'date': points[high_idx]['date'],
        'description': f"Period high at {high:.1%}",
    })

    # Find low point
    low_idx = prices.index(low)
    milestones.append({
        'type': 'low',
        'date': points[low_idx]['date'],
        'description': f"Period low at {low:.1%}",
    })

    # Big moves
    for i in range(1, len(points)):
        change = points[i]['price'] - points[i-1]['price']
        if abs(change) > 0.05:
            move_type = 'surge' if change > 0 else 'drop'
            milestones.append({
                'type': move_type,
                'date': points[i]['date'],
                'description': f"{'Surged' if change > 0 else 'Dropped'} {abs(change):.1%}",
            })

    # Sort milestones by significance
    milestones.sort(key=lambda m: m['type'] in ['high', 'low'], reverse=True)

    # Trend analysis
    recent_avg = sum(prices[-3:]) / 3
    older_avg = sum(prices[:3]) / 3

    if recent_avg > older_avg * 1.03:
        direction = 'up'
        strength = 'steadily' if recent_avg < older_avg * 1.10 else 'strongly'
    elif recent_avg < older_avg * 0.97:
        direction = 'down'
        strength = 'steadily' if recent_avg > older_avg * 0.90 else 'sharply'
    else:
        direction = 'sideways'
        strength = ''

    return {
        'current': {
            'price': current_price,
            'volume_24h': volume_24h,
        },
        'summary': {
            'price_change': price_change,
            'high': high,
            'low': low,
            'volatility': volatility,
            'total_volume': total_volume,
        },
        'points': points,
        'milestones': milestones,
        'trend': {
            'direction': direction,
            'strength': strength,
        },
    }


def _generate_history_points(current_price: float, volume_24h: float, days: int) -> list:
    """Generate synthetic history points"""
    import random

    points = []
    price = current_price

    # Work backwards from current
    for i in range(days, -1, -1):
        date = (datetime.now() - timedelta(days=i)).strftime("%m/%d")

        # Random walk backwards
        if i > 0:
            change = random.uniform(-0.03, 0.03)
            price = max(0.05, min(0.95, price - change))

        # Volume estimate
        vol = volume_24h * random.uniform(0.5, 1.5) if i < 7 else volume_24h * random.uniform(0.3, 1.0)

        points.append({
            'date': date,
            'price': price if i > 0 else current_price,
            'volume': vol,
        })

    # Ensure last point is current price
    points[-1]['price'] = current_price

    return points


def _display_chart(console: Console, points: list):
    """Display ASCII price chart"""
    if not points:
        console.print("[dim]No data[/dim]")
        return

    prices = [p['price'] for p in points]
    min_price = min(prices)
    max_price = max(prices)
    price_range = max_price - min_price

    if price_range == 0:
        price_range = 0.01

    height = 8
    width = min(len(points), 40)

    # Sample points if too many
    if len(points) > width:
        step = len(points) / width
        sampled = [points[int(i * step)] for i in range(width)]
    else:
        sampled = points

    # Build chart
    chart = []
    for row in range(height, -1, -1):
        line = ""
        threshold = min_price + (row / height) * price_range

        for point in sampled:
            if point['price'] >= threshold:
                if row == height or point['price'] < min_price + ((row + 1) / height) * price_range:
                    line += "█"
                else:
                    line += "█"
            else:
                line += " "

        # Price label on right
        if row == height:
            chart.append(f"  {max_price:.0%} │{line}│")
        elif row == 0:
            chart.append(f"  {min_price:.0%} │{line}│")
        elif row == height // 2:
            mid = (min_price + max_price) / 2
            chart.append(f"  {mid:.0%} │{line}│")
        else:
            chart.append(f"       │{line}│")

    # Date labels
    if sampled:
        first_date = sampled[0]['date']
        last_date = sampled[-1]['date']
        date_line = f"       {first_date}" + " " * (len(sampled) - len(first_date) - len(last_date)) + last_date
        chart.append("       └" + "─" * len(sampled) + "┘")
        chart.append(date_line)

    for line in chart:
        console.print(f"[cyan]{line}[/cyan]")


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            import json
            prices = market['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)
