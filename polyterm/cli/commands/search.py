"""Enhanced Market Search - Find markets with advanced filters"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.argument("query", required=False)
@click.option("--category", "-c", default=None, help="Filter by category (politics, crypto, sports, etc.)")
@click.option("--min-volume", "-v", type=float, default=None, help="Minimum volume in USD")
@click.option("--max-volume", type=float, default=None, help="Maximum volume in USD")
@click.option("--min-liquidity", "-l", type=float, default=None, help="Minimum liquidity in USD")
@click.option("--min-price", type=float, default=None, help="Minimum YES price (0-100)")
@click.option("--max-price", type=float, default=None, help="Maximum YES price (0-100)")
@click.option("--ending-soon", "-e", type=int, default=None, help="Markets ending within N days")
@click.option("--sort", "-s", type=click.Choice(["volume", "liquidity", "price", "recent"]), default="volume", help="Sort by")
@click.option("--limit", default=20, help="Maximum results (default: 20)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def search(ctx, query, category, min_volume, max_volume, min_liquidity, min_price, max_price, ending_soon, sort, limit, interactive, output_format):
    """Search markets with advanced filters

    Find markets matching specific criteria for volume, price, liquidity, and more.

    Examples:
        polyterm search "bitcoin"                          # Basic search
        polyterm search --category crypto --min-volume 100000
        polyterm search --min-price 60 --max-price 80      # Markets between 60-80%
        polyterm search --ending-soon 7                    # Ending within 7 days
        polyterm search -i                                 # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    if interactive:
        filters = _interactive_mode(console)
        if filters is None:
            return
        query = filters.get('query')
        category = filters.get('category')
        min_volume = filters.get('min_volume')
        min_liquidity = filters.get('min_liquidity')
        min_price = filters.get('min_price')
        max_price = filters.get('max_price')
        ending_soon = filters.get('ending_soon')
        sort = filters.get('sort', 'volume')

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Get markets
        if query:
            console.print(f"[dim]Searching for: {query}[/dim]")
            markets = gamma_client.search_markets(query, limit=200)
        else:
            console.print("[dim]Fetching markets...[/dim]")
            markets = gamma_client.get_markets(limit=200, active=True)

        if not markets:
            if output_format == 'json':
                print_json({'success': True, 'markets': [], 'message': 'No markets found'})
            else:
                console.print("[yellow]No markets found.[/yellow]")
            return

        # Apply filters
        filtered = _apply_filters(
            markets,
            category=category,
            min_volume=min_volume,
            max_volume=max_volume,
            min_liquidity=min_liquidity,
            min_price=min_price,
            max_price=max_price,
            ending_soon=ending_soon,
        )

        if not filtered:
            if output_format == 'json':
                print_json({'success': True, 'markets': [], 'message': 'No markets match filters'})
            else:
                console.print("[yellow]No markets match your filters.[/yellow]")
            return

        # Sort
        filtered = _sort_markets(filtered, sort)

        # Limit
        filtered = filtered[:limit]

        # Output
        if output_format == 'json':
            print_json({
                'success': True,
                'query': query,
                'filters': {
                    'category': category,
                    'min_volume': min_volume,
                    'max_volume': max_volume,
                    'min_liquidity': min_liquidity,
                    'min_price': min_price,
                    'max_price': max_price,
                    'ending_soon': ending_soon,
                },
                'sort': sort,
                'count': len(filtered),
                'markets': filtered,
            })
        else:
            _display_results(console, filtered, query, sort)

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _interactive_mode(console: Console) -> dict:
    """Interactive search mode"""
    console.print(Panel(
        "[bold]Market Search[/bold]\n\n"
        "[dim]Find markets with advanced filters.[/dim]",
        title="[cyan]Search[/cyan]",
        border_style="cyan",
    ))
    console.print()

    filters = {}

    try:
        # Query
        filters['query'] = Prompt.ask(
            "[cyan]Search term (or press Enter for all)[/cyan]",
            default=""
        ) or None

        # Category
        console.print()
        console.print("[bold]Categories:[/bold] politics, crypto, sports, science, business, culture")
        category = Prompt.ask(
            "[cyan]Category filter (or Enter for all)[/cyan]",
            default=""
        )
        filters['category'] = category if category else None

        # Volume
        console.print()
        vol_input = Prompt.ask(
            "[cyan]Minimum volume (e.g., 10000, or Enter for any)[/cyan]",
            default=""
        )
        if vol_input:
            try:
                filters['min_volume'] = float(vol_input)
            except ValueError:
                pass

        # Liquidity
        liq_input = Prompt.ask(
            "[cyan]Minimum liquidity (e.g., 5000, or Enter for any)[/cyan]",
            default=""
        )
        if liq_input:
            try:
                filters['min_liquidity'] = float(liq_input)
            except ValueError:
                pass

        # Price range
        console.print()
        console.print("[dim]Price range (0-100%)[/dim]")
        min_p = Prompt.ask("[cyan]Minimum price (or Enter for any)[/cyan]", default="")
        max_p = Prompt.ask("[cyan]Maximum price (or Enter for any)[/cyan]", default="")

        if min_p:
            try:
                filters['min_price'] = float(min_p)
            except ValueError:
                pass
        if max_p:
            try:
                filters['max_price'] = float(max_p)
            except ValueError:
                pass

        # Ending soon
        console.print()
        ending = Prompt.ask(
            "[cyan]Ending within N days (or Enter for any)[/cyan]",
            default=""
        )
        if ending:
            try:
                filters['ending_soon'] = int(ending)
            except ValueError:
                pass

        # Sort
        console.print()
        filters['sort'] = Prompt.ask(
            "[cyan]Sort by[/cyan]",
            choices=["volume", "liquidity", "price", "recent"],
            default="volume"
        )

        return filters

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return None


def _apply_filters(
    markets: list,
    category: str = None,
    min_volume: float = None,
    max_volume: float = None,
    min_liquidity: float = None,
    min_price: float = None,
    max_price: float = None,
    ending_soon: int = None,
) -> list:
    """Apply filters to market list"""
    import json

    now = datetime.now()
    filtered = []

    for market in markets:
        # Get market data
        market_id = market.get('id', market.get('condition_id', ''))
        title = market.get('question', market.get('title', ''))
        market_category = market.get('category', '').lower()

        # Get price
        outcome_prices = market.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []
        price = float(outcome_prices[0]) * 100 if outcome_prices else 50

        # Get volume and liquidity
        volume = float(market.get('volume', 0) or 0)
        liquidity = float(market.get('liquidity', 0) or 0)

        # Get end date
        end_date_str = market.get('endDate', '')
        days_remaining = None
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                end_date = end_date.replace(tzinfo=None)
                days_remaining = (end_date - now).days
            except Exception:
                pass

        # Apply filters
        if category and category.lower() not in market_category:
            continue

        if min_volume is not None and volume < min_volume:
            continue

        if max_volume is not None and volume > max_volume:
            continue

        if min_liquidity is not None and liquidity < min_liquidity:
            continue

        if min_price is not None and price < min_price:
            continue

        if max_price is not None and price > max_price:
            continue

        if ending_soon is not None:
            if days_remaining is None or days_remaining < 0 or days_remaining > ending_soon:
                continue

        filtered.append({
            'id': market_id,
            'title': title,
            'category': market_category,
            'price': price,
            'volume': volume,
            'liquidity': liquidity,
            'days_remaining': days_remaining,
        })

    return filtered


def _sort_markets(markets: list, sort_by: str) -> list:
    """Sort markets by specified field"""
    if sort_by == 'volume':
        return sorted(markets, key=lambda x: x.get('volume', 0), reverse=True)
    elif sort_by == 'liquidity':
        return sorted(markets, key=lambda x: x.get('liquidity', 0), reverse=True)
    elif sort_by == 'price':
        return sorted(markets, key=lambda x: x.get('price', 0), reverse=True)
    elif sort_by == 'recent':
        # Sort by days remaining (None last, then ascending)
        return sorted(
            markets,
            key=lambda x: (x.get('days_remaining') is None, x.get('days_remaining', 9999))
        )
    return markets


def _display_results(console: Console, markets: list, query: str, sort_by: str):
    """Display search results"""
    console.print()

    title = f"Search Results"
    if query:
        title += f': "{query}"'

    console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", style="dim", width=3)
    table.add_column("Market", max_width=45)
    table.add_column("Price", justify="right", width=7)
    table.add_column("Volume", justify="right", width=10)
    table.add_column("Liquidity", justify="right", width=10)
    table.add_column("Ends", width=8)

    for i, market in enumerate(markets, 1):
        # Format volume
        vol = market['volume']
        if vol >= 1_000_000:
            vol_str = f"${vol/1_000_000:.1f}M"
        elif vol >= 1_000:
            vol_str = f"${vol/1_000:.0f}K"
        else:
            vol_str = f"${vol:.0f}"

        # Format liquidity
        liq = market['liquidity']
        if liq >= 1_000_000:
            liq_str = f"${liq/1_000_000:.1f}M"
        elif liq >= 1_000:
            liq_str = f"${liq/1_000:.0f}K"
        else:
            liq_str = f"${liq:.0f}"

        # Format end date
        days = market.get('days_remaining')
        if days is None:
            end_str = "[dim]—[/dim]"
        elif days < 0:
            end_str = "[red]Ended[/red]"
        elif days == 0:
            end_str = "[yellow]Today[/yellow]"
        elif days == 1:
            end_str = "[yellow]Tomorrow[/yellow]"
        elif days <= 7:
            end_str = f"[yellow]{days}d[/yellow]"
        else:
            end_str = f"{days}d"

        # Price color
        price = market['price']
        if price >= 80 or price <= 20:
            price_style = "green"
        elif price >= 60 or price <= 40:
            price_style = "yellow"
        else:
            price_style = "cyan"

        table.add_row(
            str(i),
            market['title'][:43],
            f"[{price_style}]{price:.0f}%[/{price_style}]",
            vol_str,
            liq_str,
            end_str,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(markets)} market(s) found, sorted by {sort_by}[/dim]")
    console.print()

    # Quick actions
    console.print("[dim]Quick actions:[/dim]")
    console.print("[dim]  polyterm stats -m \"<market>\"      # View detailed stats[/dim]")
    console.print("[dim]  polyterm chart -m \"<market>\"      # View price chart[/dim]")
    console.print("[dim]  polyterm bookmarks --add \"<id>\"   # Bookmark a market[/dim]")
    console.print()
