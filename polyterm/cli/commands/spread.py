"""Spread Analysis - Understand true trading costs"""

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
@click.option("--amount", "-a", type=float, default=100, help="Trade amount in USD")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def spread(ctx, market_search, amount, output_format):
    """Analyze bid/ask spread and execution costs

    Understand the true cost of trading before you execute.
    Shows spread, slippage estimates, and execution quality.

    Examples:
        polyterm spread "bitcoin"              # Basic spread analysis
        polyterm spread "trump" --amount 500   # Cost for $500 trade
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        base_url=config.clob_base_url,
        api_key=config.clob_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing spread...", total=None)

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
            token_id = market.get('clobTokenIds', [None])[0] if market.get('clobTokenIds') else None

            # Get order book for spread data
            orderbook = None
            if token_id:
                try:
                    orderbook = clob_client.get_orderbook(token_id)
                except Exception:
                    pass

            # Calculate spread metrics
            spread_data = _calculate_spread(market, orderbook, amount)

    finally:
        gamma_client.close()
        clob_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'market': title,
            'trade_amount': amount,
            'spread': spread_data,
        })
        return

    # Display
    console.print()
    console.print(Panel(f"[bold]Spread Analysis[/bold]\n{title[:60]}", border_style="cyan"))
    console.print()

    # Current prices
    console.print("[bold]Current Market:[/bold]")
    console.print()

    price_table = Table(show_header=False, box=None, padding=(0, 2))
    price_table.add_column(width=15)
    price_table.add_column(justify="right", width=12)

    price_table.add_row("Best Bid", f"[green]{spread_data['best_bid']:.1%}[/green]")
    price_table.add_row("Best Ask", f"[red]{spread_data['best_ask']:.1%}[/red]")
    price_table.add_row("Mid Price", f"{spread_data['mid_price']:.1%}")
    price_table.add_row("Spread", f"{spread_data['spread_pct']:.2%}")

    console.print(price_table)
    console.print()

    # Spread quality
    quality = spread_data['quality']
    if quality == 'tight':
        quality_str = "[green]TIGHT[/green] - Low cost to trade"
    elif quality == 'normal':
        quality_str = "[yellow]NORMAL[/yellow] - Typical spread"
    elif quality == 'wide':
        quality_str = "[red]WIDE[/red] - Higher cost to trade"
    else:
        quality_str = "[red]VERY WIDE[/red] - Consider limit orders"

    console.print(f"[bold]Spread Quality:[/bold] {quality_str}")
    console.print()

    # Execution cost for trade amount
    console.print(f"[bold]Execution Cost (${amount:,.0f} trade):[/bold]")
    console.print()

    cost_table = Table(show_header=True, header_style="bold cyan", box=None)
    cost_table.add_column("", width=20)
    cost_table.add_column("YES Side", width=12, justify="right")
    cost_table.add_column("NO Side", width=12, justify="right")

    # Buy costs
    cost_table.add_row(
        "Buy at market",
        f"${spread_data['yes_buy_cost']:,.2f}",
        f"${spread_data['no_buy_cost']:,.2f}",
    )

    # Spread cost
    cost_table.add_row(
        "Spread cost",
        f"[red]${spread_data['yes_spread_cost']:,.2f}[/red]",
        f"[red]${spread_data['no_spread_cost']:,.2f}[/red]",
    )

    # Effective price
    cost_table.add_row(
        "Effective price",
        f"{spread_data['yes_effective_price']:.1%}",
        f"{spread_data['no_effective_price']:.1%}",
    )

    console.print(cost_table)
    console.print()

    # Slippage estimate
    if spread_data['slippage_estimate'] > 0:
        console.print(f"[bold]Estimated Slippage:[/bold] [yellow]{spread_data['slippage_estimate']:.2%}[/yellow]")
        console.print(f"[dim]For ${amount:,.0f} trade based on order book depth[/dim]")
        console.print()

    # Recommendations
    console.print("[bold]Recommendations:[/bold]")
    for rec in spread_data['recommendations']:
        console.print(f"  [cyan]>[/cyan] {rec}")

    console.print()


def _calculate_spread(market: dict, orderbook: dict, amount: float) -> dict:
    """Calculate spread metrics"""
    # Get basic prices
    if orderbook:
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        best_bid = float(bids[0].get('price', 0)) if bids else 0
        best_ask = float(asks[0].get('price', 1)) if asks else 1

        # Calculate depth
        total_bid_vol = sum(float(b.get('size', 0)) for b in bids[:5])
        total_ask_vol = sum(float(a.get('size', 0)) for a in asks[:5])
    else:
        # Estimate from market data
        price = _get_price(market)
        best_bid = max(0.01, price - 0.02)
        best_ask = min(0.99, price + 0.02)
        total_bid_vol = market.get('liquidity', 10000) * 0.3
        total_ask_vol = market.get('liquidity', 10000) * 0.3

    mid_price = (best_bid + best_ask) / 2
    spread_abs = best_ask - best_bid
    spread_pct = spread_abs / mid_price if mid_price > 0 else 0

    # Spread quality
    if spread_pct < 0.02:
        quality = 'tight'
    elif spread_pct < 0.05:
        quality = 'normal'
    elif spread_pct < 0.10:
        quality = 'wide'
    else:
        quality = 'very_wide'

    # Execution costs
    # YES side: buying at ask
    yes_shares = amount / best_ask if best_ask > 0 else 0
    yes_buy_cost = amount
    yes_spread_cost = (best_ask - mid_price) * yes_shares
    yes_effective_price = best_ask

    # NO side: buying at (1 - best_bid) effectively
    no_price = 1 - best_bid
    no_shares = amount / no_price if no_price > 0 else 0
    no_buy_cost = amount
    no_spread_cost = (mid_price - best_bid) * no_shares
    no_effective_price = no_price

    # Slippage estimate based on depth
    avg_depth = (total_bid_vol + total_ask_vol) / 2 if (total_bid_vol + total_ask_vol) > 0 else 1
    if amount > avg_depth:
        slippage_estimate = min(0.10, (amount / avg_depth - 1) * 0.02)
    else:
        slippage_estimate = 0

    # Recommendations
    recommendations = []

    if quality == 'tight':
        recommendations.append("Spread is tight - market orders are cost-effective")
    elif quality == 'normal':
        recommendations.append("Consider limit orders to save on spread")
    else:
        recommendations.append("Use limit orders - spread is wide")
        recommendations.append(f"Limit order at {mid_price:.1%} could save ${yes_spread_cost:.2f}")

    if slippage_estimate > 0.01:
        recommendations.append(f"Consider smaller orders to reduce slippage")

    if total_bid_vol > total_ask_vol * 1.5:
        recommendations.append("More buyers than sellers - price may rise")
    elif total_ask_vol > total_bid_vol * 1.5:
        recommendations.append("More sellers than buyers - price may fall")

    return {
        'best_bid': best_bid,
        'best_ask': best_ask,
        'mid_price': mid_price,
        'spread_abs': spread_abs,
        'spread_pct': spread_pct,
        'quality': quality,
        'yes_buy_cost': yes_buy_cost,
        'yes_spread_cost': yes_spread_cost,
        'yes_effective_price': yes_effective_price,
        'no_buy_cost': no_buy_cost,
        'no_spread_cost': no_spread_cost,
        'no_effective_price': no_effective_price,
        'slippage_estimate': slippage_estimate,
        'recommendations': recommendations,
    }


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
