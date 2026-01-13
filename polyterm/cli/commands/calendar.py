"""Market Calendar - View upcoming market resolutions"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--days", "-d", default=7, help="Days to look ahead (default: 7)")
@click.option("--limit", "-l", default=20, help="Maximum markets to show (default: 20)")
@click.option("--category", "-c", default=None, help="Filter by category (e.g., politics, crypto)")
@click.option("--bookmarked", "-b", is_flag=True, help="Only show bookmarked markets")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def calendar(ctx, days, limit, category, bookmarked, output_format):
    """View upcoming market resolutions

    Shows markets that are ending soon, helping you plan trades
    and avoid getting stuck in positions near resolution.

    Examples:
        polyterm calendar                     # Next 7 days
        polyterm calendar --days 30           # Next 30 days
        polyterm calendar --category crypto   # Crypto markets only
        polyterm calendar --bookmarked        # Only bookmarked markets
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Get bookmarked market IDs if needed
        bookmarked_ids = set()
        if bookmarked:
            bookmarks = db.get_bookmarks()
            bookmarked_ids = {b['market_id'] for b in bookmarks}
            if not bookmarked_ids:
                if output_format == 'json':
                    print_json({'success': True, 'markets': [], 'message': 'No bookmarked markets'})
                else:
                    console.print("[yellow]No bookmarked markets.[/yellow]")
                return

        # Calculate date range
        now = datetime.now()
        end_date = now + timedelta(days=days)

        # Get markets - we need to fetch more and filter
        console.print(f"[dim]Fetching markets ending in the next {days} days...[/dim]")

        # Get active markets sorted by end date
        markets = gamma_client.get_markets(limit=200, active=True)

        # Filter and sort by end date
        upcoming = []
        for market in markets:
            # Get end date
            end_date_str = market.get('endDate', '')
            if not end_date_str:
                continue

            try:
                market_end = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                # Convert to naive datetime for comparison
                market_end = market_end.replace(tzinfo=None)
            except Exception:
                continue

            # Filter by date range
            if market_end < now or market_end > end_date:
                continue

            # Filter by bookmarked
            if bookmarked:
                market_id = market.get('id', market.get('condition_id', ''))
                if market_id not in bookmarked_ids:
                    continue

            # Filter by category
            if category:
                market_category = market.get('category', '').lower()
                if category.lower() not in market_category:
                    continue

            # Get current price
            import json
            outcome_prices = market.get('outcomePrices', [])
            if isinstance(outcome_prices, str):
                try:
                    outcome_prices = json.loads(outcome_prices)
                except Exception:
                    outcome_prices = []

            current_price = float(outcome_prices[0]) if outcome_prices else 0.5
            volume = float(market.get('volume', 0) or 0)

            upcoming.append({
                'id': market.get('id', market.get('condition_id', '')),
                'title': market.get('question', market.get('title', 'Unknown')),
                'end_date': market_end,
                'price': current_price,
                'volume': volume,
                'category': market.get('category', ''),
                'liquidity': float(market.get('liquidity', 0) or 0),
            })

        # Sort by end date
        upcoming.sort(key=lambda x: x['end_date'])

        # Limit results
        upcoming = upcoming[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'days': days,
                'count': len(upcoming),
                'markets': [
                    {
                        **m,
                        'end_date': m['end_date'].isoformat(),
                    }
                    for m in upcoming
                ],
            })
            return

        if not upcoming:
            console.print(f"[yellow]No markets ending in the next {days} days.[/yellow]")
            return

        console.print()
        console.print(Panel(
            f"[bold]Market Calendar[/bold] [dim](Next {days} days)[/dim]",
            border_style="cyan",
        ))
        console.print()

        # Group by date
        current_date = None
        table = None

        for market in upcoming:
            market_date = market['end_date'].date()

            # New date group
            if market_date != current_date:
                if table:
                    console.print(table)
                    console.print()

                current_date = market_date

                # Date header
                days_until = (market_date - now.date()).days
                if days_until == 0:
                    date_label = "[bold red]TODAY[/bold red]"
                elif days_until == 1:
                    date_label = "[bold yellow]TOMORROW[/bold yellow]"
                else:
                    date_label = f"[bold]{market_date.strftime('%A, %b %d')}[/bold] [dim]({days_until} days)[/dim]"

                console.print(date_label)

                table = Table(show_header=True, header_style="bold", box=None)
                table.add_column("Time", width=6)
                table.add_column("Market", max_width=45)
                table.add_column("Price", justify="right", width=7)
                table.add_column("Volume", justify="right", width=10)

            # Format time
            time_str = market['end_date'].strftime("%H:%M")

            # Format volume
            vol = market['volume']
            if vol >= 1_000_000:
                vol_str = f"${vol/1_000_000:.1f}M"
            elif vol >= 1_000:
                vol_str = f"${vol/1_000:.0f}K"
            else:
                vol_str = f"${vol:.0f}"

            # Price color based on certainty
            price = market['price']
            if price >= 0.9 or price <= 0.1:
                price_style = "green"  # High certainty
            elif price >= 0.7 or price <= 0.3:
                price_style = "yellow"  # Moderate certainty
            else:
                price_style = "cyan"  # Uncertain

            table.add_row(
                time_str,
                market['title'][:43],
                f"[{price_style}]{price * 100:.0f}%[/{price_style}]",
                vol_str,
            )

        # Print last table
        if table:
            console.print(table)
            console.print()

        # Summary
        console.print(f"[dim]{len(upcoming)} market(s) ending in the next {days} days[/dim]")
        console.print()

        # Tips
        console.print("[dim]Tips:[/dim]")
        console.print("[dim]  - Markets near 90%+ or 10%- are likely to resolve as expected[/dim]")
        console.print("[dim]  - Consider exiting positions before resolution to avoid liquidity issues[/dim]")
        console.print("[dim]  - Use 'polyterm pricealert' to set alerts on these markets[/dim]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
