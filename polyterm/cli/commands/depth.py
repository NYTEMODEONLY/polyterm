"""Liquidity Depth Analyzer - Analyze order book depth and slippage"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", "search_term", default=None, help="Market to analyze")
@click.option("--size", "-s", type=float, default=1000, help="Trade size to analyze ($)")
@click.option("--levels", "-l", default=10, help="Number of price levels to show")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def depth(ctx, search_term, size, levels, interactive, output_format):
    """Analyze order book depth and estimate slippage

    Shows liquidity at each price level and estimates execution
    price for different trade sizes.

    Examples:
        polyterm depth -m "bitcoin"              # Analyze depth
        polyterm depth -m "election" -s 5000     # For $5000 trade
        polyterm depth --interactive             # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        search_term = Prompt.ask("[cyan]Search for market[/cyan]", default="")
        if search_term:
            size_str = Prompt.ask("[cyan]Trade size ($)[/cyan]", default="1000")
            try:
                size = float(size_str)
            except ValueError:
                size = 1000

    if not search_term:
        console.print("[yellow]Please specify a market with -m or use --interactive[/yellow]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        base_url=config.clob_base_url,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing liquidity...", total=None)

            # Find market
            markets = gamma_client.search_markets(search_term, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
                else:
                    console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
                return

            market = markets[0]
            market_id = market.get('id', market.get('condition_id', ''))
            title = market.get('question', market.get('title', ''))[:60]

            # Get CLOB token
            clob_token = market.get('clobTokenIds', [''])[0] if market.get('clobTokenIds') else ''

            if not clob_token:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'No CLOB token found for market'})
                else:
                    console.print("[yellow]Order book not available for this market.[/yellow]")
                return

            # Get order book
            orderbook = clob_client.get_orderbook(clob_token)

            if not orderbook:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Could not fetch order book'})
                else:
                    console.print("[yellow]Could not fetch order book data.[/yellow]")
                return

            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            # Analyze depth
            analysis = _analyze_depth(bids, asks, size, levels)

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'analysis': analysis,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
        console.print()

        # Summary stats
        console.print("[bold]Liquidity Summary:[/bold]")
        console.print(f"  Total Bid Depth: [green]${analysis['total_bid_depth']:,.2f}[/green]")
        console.print(f"  Total Ask Depth: [red]${analysis['total_ask_depth']:,.2f}[/red]")
        console.print(f"  Spread: {analysis['spread']:.2%} ({analysis['spread_cents']:.1f}c)")
        console.print(f"  Mid Price: {analysis['mid_price']:.4f}")
        console.print()

        # Depth visualization
        console.print("[bold]Order Book Depth:[/bold]")
        console.print()
        _display_depth_chart(console, analysis['bid_levels'], analysis['ask_levels'])
        console.print()

        # Slippage analysis
        console.print(f"[bold]Slippage Analysis (${size:,.0f} trade):[/bold]")
        console.print()

        slip_table = Table(show_header=True, header_style="bold cyan", box=None)
        slip_table.add_column("Direction", width=10)
        slip_table.add_column("Avg Price", width=12, justify="center")
        slip_table.add_column("Slippage", width=10, justify="center")
        slip_table.add_column("Cost Impact", width=12, justify="right")
        slip_table.add_column("Fillable", width=10, justify="center")

        # Buy (lift asks)
        buy_slip = analysis['buy_slippage']
        slip_table.add_row(
            "[green]BUY YES[/green]",
            f"{buy_slip['avg_price']:.4f}" if buy_slip['fillable'] else "-",
            f"{buy_slip['slippage_pct']:.2%}" if buy_slip['fillable'] else "-",
            f"[red]-${buy_slip['cost_impact']:,.2f}[/red]" if buy_slip['fillable'] else "-",
            "[green]Yes[/green]" if buy_slip['fillable'] else f"[red]No (${buy_slip['available']:,.0f})[/red]",
        )

        # Sell (hit bids)
        sell_slip = analysis['sell_slippage']
        slip_table.add_row(
            "[red]SELL YES[/red]",
            f"{sell_slip['avg_price']:.4f}" if sell_slip['fillable'] else "-",
            f"{sell_slip['slippage_pct']:.2%}" if sell_slip['fillable'] else "-",
            f"[red]-${sell_slip['cost_impact']:,.2f}[/red]" if sell_slip['fillable'] else "-",
            "[green]Yes[/green]" if sell_slip['fillable'] else f"[red]No (${sell_slip['available']:,.0f})[/red]",
        )

        console.print(slip_table)
        console.print()

        # Size recommendations
        console.print("[bold]Trade Size Recommendations:[/bold]")
        console.print()

        size_table = Table(show_header=True, header_style="bold cyan", box=None)
        size_table.add_column("Trade Size", width=12)
        size_table.add_column("Buy Slippage", width=12, justify="center")
        size_table.add_column("Sell Slippage", width=12, justify="center")
        size_table.add_column("Rating", width=10, justify="center")

        for test_size in [100, 500, 1000, 5000, 10000]:
            buy_test = _calculate_slippage(asks, test_size, analysis['mid_price'], 'buy')
            sell_test = _calculate_slippage(bids, test_size, analysis['mid_price'], 'sell')

            avg_slip = (buy_test['slippage_pct'] + sell_test['slippage_pct']) / 2

            if not buy_test['fillable'] or not sell_test['fillable']:
                rating = "[red]Too Large[/red]"
            elif avg_slip < 0.005:
                rating = "[green]Excellent[/green]"
            elif avg_slip < 0.02:
                rating = "[bright_green]Good[/bright_green]"
            elif avg_slip < 0.05:
                rating = "[yellow]Fair[/yellow]"
            else:
                rating = "[red]Poor[/red]"

            size_table.add_row(
                f"${test_size:,}",
                f"{buy_test['slippage_pct']:.2%}" if buy_test['fillable'] else "[red]No Fill[/red]",
                f"{sell_test['slippage_pct']:.2%}" if sell_test['fillable'] else "[red]No Fill[/red]",
                rating,
            )

        console.print(size_table)
        console.print()

        # Liquidity score
        liquidity_score = _calculate_liquidity_score(analysis)
        score_color = "green" if liquidity_score >= 70 else "yellow" if liquidity_score >= 40 else "red"
        console.print(f"[bold]Liquidity Score:[/bold] [{score_color}]{liquidity_score}/100[/{score_color}]")
        console.print()

        if liquidity_score < 40:
            console.print("[yellow]Warning: Low liquidity. Consider using limit orders.[/yellow]")
        elif liquidity_score < 70:
            console.print("[dim]Moderate liquidity. Watch for slippage on larger trades.[/dim]")
        else:
            console.print("[dim]Good liquidity. Market orders should execute well.[/dim]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()


def _analyze_depth(bids: list, asks: list, trade_size: float, levels: int) -> dict:
    """Analyze order book depth"""
    # Parse and sort orders
    parsed_bids = []
    for bid in bids:
        try:
            price = float(bid.get('price', 0))
            size = float(bid.get('size', 0))
            if price > 0 and size > 0:
                parsed_bids.append({'price': price, 'size': size, 'value': price * size})
        except (ValueError, TypeError):
            continue

    parsed_asks = []
    for ask in asks:
        try:
            price = float(ask.get('price', 0))
            size = float(ask.get('size', 0))
            if price > 0 and size > 0:
                parsed_asks.append({'price': price, 'size': size, 'value': price * size})
        except (ValueError, TypeError):
            continue

    # Sort: bids descending (best bid first), asks ascending (best ask first)
    parsed_bids.sort(key=lambda x: x['price'], reverse=True)
    parsed_asks.sort(key=lambda x: x['price'])

    # Calculate totals
    total_bid_depth = sum(b['value'] for b in parsed_bids)
    total_ask_depth = sum(a['value'] for a in parsed_asks)

    # Best prices
    best_bid = parsed_bids[0]['price'] if parsed_bids else 0
    best_ask = parsed_asks[0]['price'] if parsed_asks else 1

    spread = best_ask - best_bid if best_bid > 0 else 0
    mid_price = (best_bid + best_ask) / 2 if best_bid > 0 else best_ask

    # Aggregate by price level
    bid_levels = _aggregate_levels(parsed_bids, levels)
    ask_levels = _aggregate_levels(parsed_asks, levels)

    # Calculate slippage for trade size
    buy_slippage = _calculate_slippage(parsed_asks, trade_size, mid_price, 'buy')
    sell_slippage = _calculate_slippage(parsed_bids, trade_size, mid_price, 'sell')

    return {
        'total_bid_depth': total_bid_depth,
        'total_ask_depth': total_ask_depth,
        'best_bid': best_bid,
        'best_ask': best_ask,
        'spread': spread,
        'spread_cents': spread * 100,
        'mid_price': mid_price,
        'bid_levels': bid_levels,
        'ask_levels': ask_levels,
        'buy_slippage': buy_slippage,
        'sell_slippage': sell_slippage,
    }


def _aggregate_levels(orders: list, num_levels: int) -> list:
    """Aggregate orders into price levels"""
    if not orders:
        return []

    # Group by price
    levels = {}
    for order in orders:
        price = round(order['price'], 2)  # Round to cents
        if price not in levels:
            levels[price] = {'price': price, 'size': 0, 'value': 0}
        levels[price]['size'] += order['size']
        levels[price]['value'] += order['value']

    # Sort and return top levels
    sorted_levels = sorted(levels.values(), key=lambda x: x['value'], reverse=True)
    return sorted_levels[:num_levels]


def _calculate_slippage(orders: list, trade_size: float, mid_price: float, direction: str) -> dict:
    """Calculate slippage for a given trade size"""
    if not orders or trade_size <= 0:
        return {
            'avg_price': 0,
            'slippage_pct': 0,
            'cost_impact': 0,
            'fillable': False,
            'available': 0,
        }

    remaining = trade_size
    total_cost = 0
    total_shares = 0

    for order in orders:
        if remaining <= 0:
            break

        order_value = order['price'] * order['size']
        fill_value = min(remaining, order_value)
        fill_shares = fill_value / order['price'] if order['price'] > 0 else 0

        total_cost += fill_value
        total_shares += fill_shares
        remaining -= fill_value

    fillable = remaining <= 0
    available = trade_size - remaining

    if total_shares > 0:
        avg_price = total_cost / total_shares
        slippage_pct = abs(avg_price - mid_price) / mid_price if mid_price > 0 else 0
        cost_impact = abs(avg_price - mid_price) * total_shares
    else:
        avg_price = 0
        slippage_pct = 0
        cost_impact = 0

    return {
        'avg_price': avg_price,
        'slippage_pct': slippage_pct,
        'cost_impact': cost_impact,
        'fillable': fillable,
        'available': available,
    }


def _display_depth_chart(console: Console, bid_levels: list, ask_levels: list):
    """Display ASCII depth chart"""
    max_value = max(
        max((l['value'] for l in bid_levels), default=0),
        max((l['value'] for l in ask_levels), default=0),
    )

    if max_value == 0:
        console.print("[dim]No depth data available[/dim]")
        return

    chart_width = 20

    # Display asks (in reverse so lowest ask is at bottom)
    console.print("[dim]        ASKS (sell pressure)[/dim]")
    for level in reversed(ask_levels[:5]):
        bar_len = int((level['value'] / max_value) * chart_width)
        bar = "[red]" + "█" * bar_len + "[/red]"
        console.print(f"  {level['price']:.2f} |{bar} ${level['value']:,.0f}")

    # Spread line
    console.print("  " + "-" * 35)

    # Display bids
    for level in bid_levels[:5]:
        bar_len = int((level['value'] / max_value) * chart_width)
        bar = "[green]" + "█" * bar_len + "[/green]"
        console.print(f"  {level['price']:.2f} |{bar} ${level['value']:,.0f}")

    console.print("[dim]        BIDS (buy support)[/dim]")


def _calculate_liquidity_score(analysis: dict) -> int:
    """Calculate overall liquidity score (0-100)"""
    score = 0

    # Spread score (lower is better)
    spread = analysis['spread']
    if spread < 0.01:
        score += 30
    elif spread < 0.02:
        score += 25
    elif spread < 0.05:
        score += 15
    elif spread < 0.10:
        score += 5

    # Depth score
    total_depth = analysis['total_bid_depth'] + analysis['total_ask_depth']
    if total_depth > 100000:
        score += 30
    elif total_depth > 50000:
        score += 25
    elif total_depth > 10000:
        score += 15
    elif total_depth > 1000:
        score += 5

    # Balance score (bid/ask ratio close to 1 is better)
    if analysis['total_ask_depth'] > 0:
        ratio = analysis['total_bid_depth'] / analysis['total_ask_depth']
        if 0.8 <= ratio <= 1.2:
            score += 20
        elif 0.5 <= ratio <= 2.0:
            score += 10

    # Slippage score
    avg_slip = (analysis['buy_slippage']['slippage_pct'] + analysis['sell_slippage']['slippage_pct']) / 2
    if avg_slip < 0.01:
        score += 20
    elif avg_slip < 0.02:
        score += 15
    elif avg_slip < 0.05:
        score += 10
    elif avg_slip < 0.10:
        score += 5

    return min(100, score)
