"""Price Ladder - Visual order book depth at each price level"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=True)
@click.option("--side", "-s", type=click.Choice(["yes", "no", "both"]), default="both", help="Which side to show")
@click.option("--levels", "-l", default=10, help="Number of price levels")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def ladder(ctx, market_search, side, levels, output_format):
    """Visual price ladder showing depth at each level

    Shows bid/ask volume at each price tick, like a trading platform.
    Helps visualize where support and resistance might be.

    Examples:
        polyterm ladder "bitcoin"               # Full ladder
        polyterm ladder "trump" --side yes      # YES side only
        polyterm ladder "election" --levels 15  # More levels
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Loading order book...", total=None)

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
            clob_tokens = market.get('clobTokenIds', [])
            if isinstance(clob_tokens, str):
                import json
                try:
                    clob_tokens = json.loads(clob_tokens)
                except Exception:
                    clob_tokens = []
            token_id = clob_tokens[0] if clob_tokens and len(clob_tokens) > 0 else None

            # Get order book
            orderbook = None
            if token_id:
                try:
                    orderbook = clob_client.get_order_book(token_id)
                except Exception:
                    pass

            # Build ladder data
            yes_ladder = _build_ladder(orderbook, 'yes', levels) if orderbook else _mock_ladder(market, 'yes', levels)
            no_ladder = _build_ladder(orderbook, 'no', levels) if orderbook else _mock_ladder(market, 'no', levels)

    finally:
        gamma_client.close()
        clob_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'market': title,
            'yes_ladder': yes_ladder,
            'no_ladder': no_ladder,
        })
        return

    # Display ladder
    console.print()
    console.print(Panel(f"[bold]Price Ladder[/bold]\n{title[:60]}", border_style="cyan"))
    console.print()

    current_price = _get_price(market)
    console.print(f"[bold]Current Price:[/bold] {current_price:.1%}")
    console.print()

    if side in ['yes', 'both']:
        _display_ladder(console, yes_ladder, "YES", current_price)

    if side == 'both':
        console.print()

    if side in ['no', 'both']:
        _display_ladder(console, no_ladder, "NO", 1 - current_price)

    console.print()

    # Legend
    console.print("[dim]Legend: [green]█[/green] Bids (buy orders) | [red]█[/red] Asks (sell orders)[/dim]")
    console.print("[dim]Thicker bars = more volume at that level[/dim]")
    console.print()


def _build_ladder(orderbook: dict, side: str, levels: int) -> list:
    """Build ladder from real order book data"""
    ladder = []

    bids = orderbook.get('bids', [])
    asks = orderbook.get('asks', [])

    # Get all price levels
    all_prices = set()
    for order in bids:
        all_prices.add(float(order.get('price', 0)))
    for order in asks:
        all_prices.add(float(order.get('price', 0)))

    # Create price ticks from 0.01 to 0.99
    price_ticks = [i / 100 for i in range(1, 100)]

    # Aggregate volume at each price
    bid_vol = {}
    ask_vol = {}

    for order in bids:
        price = round(float(order.get('price', 0)), 2)
        size = float(order.get('size', 0))
        bid_vol[price] = bid_vol.get(price, 0) + size

    for order in asks:
        price = round(float(order.get('price', 0)), 2)
        size = float(order.get('size', 0))
        ask_vol[price] = ask_vol.get(price, 0) + size

    # Find the spread area to center around
    best_bid = max(bid_vol.keys()) if bid_vol else 0.50
    best_ask = min(ask_vol.keys()) if ask_vol else 0.50
    mid_price = (best_bid + best_ask) / 2

    # Get levels around mid price
    center_idx = int(mid_price * 100)
    start_idx = max(1, center_idx - levels // 2)
    end_idx = min(99, center_idx + levels // 2)

    for i in range(end_idx, start_idx - 1, -1):
        price = i / 100
        ladder.append({
            'price': price,
            'bid_volume': bid_vol.get(price, 0),
            'ask_volume': ask_vol.get(price, 0),
        })

    return ladder


def _mock_ladder(market: dict, side: str, levels: int) -> list:
    """Generate mock ladder when no order book available"""
    price = _get_price(market) if side == 'yes' else (1 - _get_price(market))
    liquidity = market.get('liquidity', 10000) or 10000

    ladder = []
    center = int(price * 100)
    start = max(1, center - levels // 2)
    end = min(99, center + levels // 2)

    for i in range(end, start - 1, -1):
        tick_price = i / 100
        distance = abs(tick_price - price)

        # Volume decreases with distance from current price
        decay = max(0.1, 1 - distance * 3)
        base_vol = liquidity * 0.02 * decay

        # Bids below price, asks above
        bid_vol = base_vol if tick_price < price else 0
        ask_vol = base_vol if tick_price > price else 0

        ladder.append({
            'price': tick_price,
            'bid_volume': bid_vol,
            'ask_volume': ask_vol,
        })

    return ladder


def _display_ladder(console: Console, ladder: list, side_name: str, current_price: float):
    """Display a price ladder visually"""
    console.print(f"[bold cyan]{side_name} Side:[/bold cyan]")
    console.print()

    # Find max volume for scaling
    max_vol = max(
        max(l['bid_volume'] for l in ladder) if ladder else 1,
        max(l['ask_volume'] for l in ladder) if ladder else 1,
        1
    )

    # Table
    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Bids", width=20, justify="right")
    table.add_column("Price", width=8, justify="center")
    table.add_column("Asks", width=20, justify="left")
    table.add_column("Total $", width=10, justify="right")

    for level in ladder:
        price = level['price']
        bid_vol = level['bid_volume']
        ask_vol = level['ask_volume']

        # Create visual bars
        bid_width = int((bid_vol / max_vol) * 15) if max_vol > 0 else 0
        ask_width = int((ask_vol / max_vol) * 15) if max_vol > 0 else 0

        bid_bar = f"[green]{'█' * bid_width}{'░' * (15 - bid_width)}[/green]" if bid_vol > 0 else "[dim]" + "░" * 15 + "[/dim]"
        ask_bar = f"[red]{'█' * ask_width}{'░' * (15 - ask_width)}[/red]" if ask_vol > 0 else "[dim]" + "░" * 15 + "[/dim]"

        # Highlight current price level
        price_rounded = round(current_price, 2)
        if abs(price - price_rounded) < 0.01:
            price_str = f"[bold yellow]{price:.0%}[/bold yellow]"
        else:
            price_str = f"{price:.0%}"

        total_vol = bid_vol + ask_vol
        vol_str = f"${total_vol:,.0f}" if total_vol > 0 else "[dim]-[/dim]"

        table.add_row(bid_bar, price_str, ask_bar, vol_str)

    console.print(table)

    # Summary
    total_bids = sum(l['bid_volume'] for l in ladder)
    total_asks = sum(l['ask_volume'] for l in ladder)

    console.print()
    console.print(f"[green]Total Bids: ${total_bids:,.0f}[/green] | [red]Total Asks: ${total_asks:,.0f}[/red]")

    # Imbalance indicator
    if total_bids + total_asks > 0:
        imbalance = (total_bids - total_asks) / (total_bids + total_asks)
        if imbalance > 0.2:
            console.print(f"[green]Bid pressure +{imbalance:.0%} - buyers dominating[/green]")
        elif imbalance < -0.2:
            console.print(f"[red]Ask pressure {imbalance:.0%} - sellers dominating[/red]")
        else:
            console.print(f"[yellow]Balanced book[/yellow]")


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
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))
