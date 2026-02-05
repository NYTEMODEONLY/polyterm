"""Hot Markets - See what's moving right now"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--limit", "-l", default=15, help="Number of markets to show")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--gainers", "-g", is_flag=True, help="Show only gainers")
@click.option("--losers", is_flag=True, help="Show only losers")
@click.option("--volume", "-v", is_flag=True, help="Sort by volume instead of price change")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def hot(ctx, limit, category, gainers, losers, volume, output_format):
    """See what markets are moving right now

    Shows the biggest price movers and highest volume markets.

    Examples:
        polyterm hot                     # Top movers
        polyterm hot --gainers           # Only gainers
        polyterm hot --losers            # Only losers
        polyterm hot --volume            # By volume
        polyterm hot -c crypto           # Crypto only
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
            progress.add_task("Scanning hot markets...", total=None)

            # Get active markets
            markets = gamma_client.get_markets(limit=200, active=True)

            if category:
                category_lower = category.lower()
                markets = [m for m in markets if category_lower in m.get('category', '').lower()]

            # Calculate price changes and sort
            hot_markets = []
            for market in markets:
                price_change = _get_price_change(market)
                current_price = _get_price(market)
                volume_24h = float(market.get('volume24hr', market.get('volume24h', 0)) or 0)

                # Filter by direction
                if gainers and price_change <= 0:
                    continue
                if losers and price_change >= 0:
                    continue

                hot_markets.append({
                    'market': market,
                    'price_change': price_change,
                    'current_price': current_price,
                    'volume_24h': volume_24h,
                    'abs_change': abs(price_change),
                })

            # Sort
            if volume:
                hot_markets.sort(key=lambda x: x['volume_24h'], reverse=True)
            else:
                hot_markets.sort(key=lambda x: x['abs_change'], reverse=True)

            hot_markets = hot_markets[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'count': len(hot_markets),
                'markets': [{
                    'id': h['market'].get('id', h['market'].get('condition_id', '')),
                    'title': h['market'].get('question', h['market'].get('title', '')),
                    'price': h['current_price'],
                    'price_change_24h': h['price_change'],
                    'volume_24h': h['volume_24h'],
                } for h in hot_markets],
            })
            return

        # Display results
        console.print()

        if gainers:
            title = "Top Gainers"
        elif losers:
            title = "Top Losers"
        elif volume:
            title = "Highest Volume"
        else:
            title = "Hot Markets"

        console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
        console.print()

        if not hot_markets:
            console.print("[yellow]No markets found matching criteria.[/yellow]")
            return

        # Gainers section
        if not losers:
            gainers_list = [h for h in hot_markets if h['price_change'] > 0]
            if gainers_list and not volume:
                console.print("[bold green]GAINERS[/bold green]")
                _display_hot_table(console, gainers_list[:8], show_volume=volume)
                console.print()

        # Losers section
        if not gainers:
            losers_list = [h for h in hot_markets if h['price_change'] < 0]
            if losers_list and not volume:
                console.print("[bold red]LOSERS[/bold red]")
                _display_hot_table(console, losers_list[:8], show_volume=volume)
                console.print()

        # Volume section or single table
        if volume:
            _display_hot_table(console, hot_markets, show_volume=True)
            console.print()

        # Market pulse
        console.print("[bold]Market Pulse:[/bold]")
        _display_market_pulse(console, hot_markets)
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _get_price(market: dict) -> float:
    """Get current market price"""
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


def _get_price_change(market: dict) -> float:
    """Get 24h price change"""
    price_change = market.get('priceChange24h', 0)
    if price_change:
        return price_change

    # Try calculating from other fields
    current = _get_price(market)
    prev = market.get('price24hAgo', 0)
    if prev and prev > 0:
        return (current - prev) / prev

    return 0


def _display_hot_table(console: Console, hot_markets: list, show_volume: bool = False):
    """Display hot markets table"""
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Market", max_width=45)
    table.add_column("Price", width=8, justify="center")
    table.add_column("24h", width=8, justify="right")
    if show_volume:
        table.add_column("Volume", width=12, justify="right")

    for h in hot_markets:
        market = h['market']
        title = market.get('question', market.get('title', ''))[:43]

        # Price
        price_str = f"{h['current_price']:.0%}"

        # Change with color
        change = h['price_change']
        if change > 0:
            change_str = f"[green]+{change:.1%}[/green]"
        elif change < 0:
            change_str = f"[red]{change:.1%}[/red]"
        else:
            change_str = f"[dim]0%[/dim]"

        if show_volume:
            vol_str = _format_volume(h['volume_24h'])
            table.add_row(title, price_str, change_str, vol_str)
        else:
            table.add_row(title, price_str, change_str)

    console.print(table)


def _display_market_pulse(console: Console, hot_markets: list):
    """Display market pulse summary"""
    if not hot_markets:
        return

    total = len(hot_markets)
    gainers = sum(1 for h in hot_markets if h['price_change'] > 0)
    losers = sum(1 for h in hot_markets if h['price_change'] < 0)
    unchanged = total - gainers - losers

    # Sentiment
    if gainers > losers * 1.5:
        sentiment = "[green]Bullish[/green]"
    elif losers > gainers * 1.5:
        sentiment = "[red]Bearish[/red]"
    else:
        sentiment = "[yellow]Mixed[/yellow]"

    console.print(f"  Gainers: [green]{gainers}[/green] | Losers: [red]{losers}[/red] | Unchanged: {unchanged}")
    console.print(f"  Overall Sentiment: {sentiment}")

    # Biggest moves
    if hot_markets:
        biggest = max(hot_markets, key=lambda x: x['abs_change'])
        direction = "up" if biggest['price_change'] > 0 else "down"
        console.print(f"  Biggest Move: {biggest['price_change']:+.1%} ({direction})")

    # Total volume
    total_vol = sum(h['volume_24h'] for h in hot_markets)
    console.print(f"  24h Volume: {_format_volume(total_vol)}")


def _format_volume(vol: float) -> str:
    """Format volume for display"""
    if vol >= 1_000_000:
        return f"${vol/1_000_000:.1f}M"
    elif vol >= 1_000:
        return f"${vol/1_000:.1f}K"
    else:
        return f"${vol:.0f}"
