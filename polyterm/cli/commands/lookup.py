"""Quick Lookup - Fast market information"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.argument("query", nargs=-1)
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def lookup(ctx, query, output_format):
    """Quick market lookup - fast info at a glance

    Get quick information about a market without navigating menus.
    Just type what you're looking for.

    Examples:
        polyterm lookup bitcoin           # Quick bitcoin market info
        polyterm lookup "trump win"       # Search phrase
        polyterm lookup 0x123...          # By market ID
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    search_term = ' '.join(query) if query else ''

    if not search_term:
        console.print("[yellow]Usage: polyterm lookup <market>[/yellow]")
        console.print("[dim]Example: polyterm lookup bitcoin[/dim]")
        return

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
            progress.add_task("Looking up...", total=None)

            # Search for market
            markets = gamma_client.search_markets(search_term, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
                else:
                    console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
                return

            market = markets[0]

            # Track as recently viewed
            try:
                market_id = market.get('id', market.get('condition_id', ''))
                title = market.get('question', market.get('title', ''))
                db.add_recent_market(market_id, title)
            except Exception:
                pass

        # Extract market info
        market_id = market.get('id', market.get('condition_id', ''))
        title = market.get('question', market.get('title', ''))
        category = market.get('category', 'Unknown')
        current_price = _get_price(market)
        price_change = _get_price_change(market)
        volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
        volume_total = market.get('volume', 0) or 0
        liquidity = market.get('liquidity', 0) or 0
        end_date = market.get('endDate', market.get('end_date_iso', ''))

        if output_format == 'json':
            print_json({
                'success': True,
                'market': {
                    'id': market_id,
                    'title': title,
                    'category': category,
                    'price': current_price,
                    'price_change_24h': price_change,
                    'volume_24h': volume_24h,
                    'volume_total': volume_total,
                    'liquidity': liquidity,
                    'end_date': end_date,
                }
            })
            return

        # Display quick info
        console.print()

        # Price bar visualization
        price_bar = _create_price_bar(current_price)

        # Change indicator
        if price_change > 0:
            change_str = f"[green]+{price_change:.1%}[/green]"
            arrow = "[green]↑[/green]"
        elif price_change < 0:
            change_str = f"[red]{price_change:.1%}[/red]"
            arrow = "[red]↓[/red]"
        else:
            change_str = "[dim]0%[/dim]"
            arrow = "[dim]→[/dim]"

        # Main display
        console.print(Panel(
            f"[bold]{title}[/bold]\n"
            f"[dim]{category}[/dim]",
            border_style="cyan"
        ))
        console.print()

        # Big price display
        console.print(f"  {arrow} [bold bright_white]{current_price:.0%}[/bold bright_white] YES  {change_str} 24h")
        console.print(f"     {price_bar}")
        console.print()

        # Quick stats
        stats_table = Table(show_header=False, box=None, padding=(0, 3))
        stats_table.add_column(width=15)
        stats_table.add_column(justify="right")
        stats_table.add_column(width=15)
        stats_table.add_column(justify="right")

        stats_table.add_row(
            "24h Volume",
            _format_num(volume_24h),
            "Total Volume",
            _format_num(volume_total),
        )
        stats_table.add_row(
            "Liquidity",
            _format_num(liquidity),
            "NO Price",
            f"{1-current_price:.0%}",
        )

        console.print(stats_table)
        console.print()

        # End date
        if end_date:
            try:
                if 'T' in end_date:
                    end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    end_dt = end_dt.replace(tzinfo=None)
                else:
                    end_dt = datetime.fromisoformat(end_date)

                days_left = (end_dt - datetime.now()).days
                if days_left < 0:
                    end_str = "[red]Ended[/red]"
                elif days_left == 0:
                    end_str = "[yellow]Ends today[/yellow]"
                elif days_left == 1:
                    end_str = "[yellow]Ends tomorrow[/yellow]"
                else:
                    end_str = f"[dim]Ends in {days_left} days[/dim]"

                console.print(f"  {end_str} ({end_dt.strftime('%b %d, %Y')})")
            except Exception:
                pass

        console.print()

        # Quick actions hint
        console.print("[dim]Quick actions:[/dim]")
        console.print(f"[dim]  polyterm trade -m \"{search_term}\" -a 100   # Analyze trade[/dim]")
        console.print(f"[dim]  polyterm sentiment -m \"{search_term}\"      # Check sentiment[/dim]")
        console.print(f"[dim]  polyterm depth -m \"{search_term}\"          # Check liquidity[/dim]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


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
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)


def _get_price_change(market: dict) -> float:
    """Get 24h price change"""
    price_change = market.get('priceChange24h', 0)
    if price_change:
        return price_change

    current = _get_price(market)
    prev = market.get('price24hAgo', 0)
    if prev and prev > 0:
        return (current - prev) / prev

    return 0


def _create_price_bar(price: float) -> str:
    """Create ASCII price bar"""
    width = 30
    filled = int(price * width)

    bar = ""
    for i in range(width):
        if i < filled:
            if price > 0.7:
                bar += "[green]█[/green]"
            elif price > 0.3:
                bar += "[yellow]█[/yellow]"
            else:
                bar += "[red]█[/red]"
        else:
            bar += "[dim]░[/dim]"

    return f"0% {bar} 100%"


def _format_num(num: float) -> str:
    """Format number for display"""
    if num >= 1_000_000:
        return f"${num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"${num/1_000:.1f}K"
    else:
        return f"${num:.0f}"
