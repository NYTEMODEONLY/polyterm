"""Event Timeline - Visual timeline of market resolutions"""

import click
from datetime import datetime, timedelta
from collections import defaultdict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--days", "-d", default=30, help="Days to look ahead")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--bookmarked", "-b", is_flag=True, help="Show only bookmarked markets")
@click.option("--limit", "-l", default=50, help="Maximum markets to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def timeline(ctx, days, category, bookmarked, limit, output_format):
    """Visual timeline of upcoming market resolutions

    Shows when markets are scheduled to resolve, grouped by time period.

    Examples:
        polyterm timeline                    # Next 30 days
        polyterm timeline --days 7           # Next week
        polyterm timeline --category crypto  # Crypto markets only
        polyterm timeline --bookmarked       # Your bookmarked markets
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

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
            progress.add_task("Loading timeline...", total=None)

            now = datetime.now()
            end_date = now + timedelta(days=days)

            # Get markets
            if bookmarked:
                bookmarks = db.get_bookmarks()
                markets = []
                for bm in bookmarks:
                    results = gamma_client.search_markets(bm['market_id'], limit=1)
                    if results:
                        markets.extend(results)
            else:
                # Get active markets
                markets = gamma_client.get_markets(limit=200, active=True)

            # Filter by category
            if category:
                category_lower = category.lower()
                markets = [m for m in markets if category_lower in m.get('category', '').lower()]

            # Parse and filter by end date
            events = []
            for market in markets:
                end_date_str = market.get('endDate', market.get('end_date_iso', ''))
                if not end_date_str:
                    continue

                try:
                    if 'T' in end_date_str:
                        market_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        market_end = market_end.replace(tzinfo=None)
                    else:
                        market_end = datetime.fromisoformat(end_date_str)
                except Exception:
                    continue

                # Filter by date range
                if market_end < now or market_end > end_date:
                    continue

                events.append({
                    'market': market,
                    'end_date': market_end,
                    'days_until': (market_end - now).days,
                })

            # Sort by end date
            events.sort(key=lambda x: x['end_date'])
            events = events[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'count': len(events),
                'events': [{
                    'market_id': e['market'].get('id', e['market'].get('condition_id', '')),
                    'title': e['market'].get('question', e['market'].get('title', '')),
                    'category': e['market'].get('category', ''),
                    'end_date': e['end_date'].isoformat(),
                    'days_until': e['days_until'],
                } for e in events],
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]Market Resolution Timeline[/bold]\n[dim]Next {days} days[/dim]", border_style="cyan"))
        console.print()

        if not events:
            console.print("[yellow]No market resolutions found in this time period.[/yellow]")
            return

        # Group by time period
        today = []
        tomorrow = []
        this_week = []
        next_week = []
        this_month = []
        later = []

        for event in events:
            days_until = event['days_until']
            if days_until == 0:
                today.append(event)
            elif days_until == 1:
                tomorrow.append(event)
            elif days_until <= 7:
                this_week.append(event)
            elif days_until <= 14:
                next_week.append(event)
            elif days_until <= 30:
                this_month.append(event)
            else:
                later.append(event)

        # Display timeline
        _display_timeline_section(console, "TODAY", today, "red", "!")
        _display_timeline_section(console, "TOMORROW", tomorrow, "yellow", ">")
        _display_timeline_section(console, "THIS WEEK", this_week, "cyan", "-")
        _display_timeline_section(console, "NEXT WEEK", next_week, "blue", "-")
        _display_timeline_section(console, "THIS MONTH", this_month, "dim", ".")
        _display_timeline_section(console, "LATER", later, "dim", ".")

        # Summary
        console.print()
        console.print("[bold]Summary:[/bold]")
        console.print(f"  Total events: {len(events)}")
        console.print(f"  Resolving today: {len(today)}")
        console.print(f"  Resolving this week: {len(today) + len(tomorrow) + len(this_week)}")
        console.print()

        # Visual timeline bar
        console.print("[bold]Visual Timeline:[/bold]")
        _display_visual_timeline(console, events, days)
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _display_timeline_section(console: Console, label: str, events: list, color: str, marker: str):
    """Display a section of the timeline"""
    if not events:
        return

    console.print(f"[bold {color}]{marker * 3} {label} ({len(events)})[/bold {color}]")
    console.print()

    for event in events[:10]:  # Limit per section
        market = event['market']
        title = market.get('question', market.get('title', ''))[:55]
        price = _get_price(market)
        category = market.get('category', '')[:15]

        # Format time
        end_date = event['end_date']
        if event['days_until'] == 0:
            time_str = end_date.strftime("%H:%M")
        else:
            time_str = end_date.strftime("%b %d")

        # Price color
        if price > 0.7:
            price_color = "green"
        elif price < 0.3:
            price_color = "red"
        else:
            price_color = "yellow"

        console.print(f"  [{color}]{time_str}[/{color}] [{price_color}]{price:.0%}[/{price_color}] {title}")

    if len(events) > 10:
        console.print(f"  [dim]... and {len(events) - 10} more[/dim]")

    console.print()


def _display_visual_timeline(console: Console, events: list, total_days: int):
    """Display ASCII visual timeline"""
    if not events:
        return

    # Create buckets for each day
    buckets = defaultdict(int)
    for event in events:
        day = event['days_until']
        buckets[day] += 1

    # Determine scale
    max_count = max(buckets.values()) if buckets else 1
    bar_width = 50

    console.print()

    # Week markers
    week_line = ""
    for i in range(min(total_days, bar_width)):
        if i % 7 == 0:
            week_line += "|"
        else:
            week_line += " "
    console.print(f"  {week_line}")

    # Main timeline bar
    timeline = ""
    for i in range(min(total_days, bar_width)):
        count = buckets.get(i, 0)
        if count == 0:
            timeline += "[dim]-[/dim]"
        elif count <= max_count * 0.3:
            timeline += "[green]o[/green]"
        elif count <= max_count * 0.6:
            timeline += "[yellow]O[/yellow]"
        else:
            timeline += "[red]@[/red]"

    console.print(f"  {timeline}")

    # Labels
    console.print(f"  [dim]Today{' ' * (bar_width - 15)}+{total_days}d[/dim]")
    console.print()

    # Legend
    console.print("[dim]  Legend: - none  o few  O some  @ many[/dim]")


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))
