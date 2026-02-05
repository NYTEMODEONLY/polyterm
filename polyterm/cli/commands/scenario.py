"""Scenario Analysis - What-if outcome modeling"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", default=None, help="Specific market to analyze")
@click.option("--portfolio", "-p", is_flag=True, help="Analyze full portfolio")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def scenario(ctx, market, portfolio, output_format):
    """Model what-if scenarios for your positions

    See how your portfolio would be affected by different outcomes.
    Calculate P&L for YES wins, NO wins, or specific probabilities.

    Examples:
        polyterm scenario --market "bitcoin"   # Analyze one market
        polyterm scenario --portfolio          # Analyze all positions
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    if market:
        _analyze_market_scenario(console, config, market, output_format)
    elif portfolio:
        _analyze_portfolio_scenario(console, config, db, output_format)
    else:
        # Default to portfolio if positions exist
        positions = db.get_positions(status='open')
        if positions:
            _analyze_portfolio_scenario(console, config, db, output_format)
        else:
            console.print()
            console.print(Panel("[bold]Scenario Analysis[/bold]", border_style="cyan"))
            console.print()
            console.print("[yellow]No open positions to analyze.[/yellow]")
            console.print()
            console.print("Options:")
            console.print("  [cyan]polyterm scenario --market <name>[/cyan]  Analyze a specific market")
            console.print("  [cyan]polyterm position --add[/cyan]            Add a position first")
            console.print()


def _analyze_market_scenario(console: Console, config, market_search: str, output_format: str):
    """Analyze scenarios for a specific market"""
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
            progress.add_task("Loading market...", total=None)

            markets = gamma_client.search_markets(market_search, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Market not found'})
                else:
                    console.print(f"[yellow]Market '{market_search}' not found.[/yellow]")
                return

            market = markets[0]
            title = market.get('question', market.get('title', ''))
            price = _get_price(market)

    finally:
        gamma_client.close()

    # Calculate scenarios
    scenarios = _calculate_market_scenarios(price)

    if output_format == 'json':
        print_json({
            'success': True,
            'market': title,
            'current_price': price,
            'scenarios': scenarios,
        })
        return

    # Display
    console.print()
    console.print(Panel(f"[bold]Scenario Analysis[/bold]\n{title[:60]}", border_style="cyan"))
    console.print()

    console.print(f"[bold]Current Price:[/bold] {price:.1%}")
    console.print()

    console.print("[bold]If you buy $100 of YES:[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Outcome", width=20)
    table.add_column("Your Shares", width=12, justify="right")
    table.add_column("Payout", width=12, justify="right")
    table.add_column("P&L", width=12, justify="right")
    table.add_column("ROI", width=10, justify="right")

    buy_amount = 100
    shares = buy_amount / price

    # YES wins scenario
    payout = shares * 1.0
    pnl = payout - buy_amount
    roi = pnl / buy_amount

    table.add_row(
        "[green]YES Wins[/green]",
        f"{shares:.1f}",
        f"[green]${payout:.2f}[/green]",
        f"[green]+${pnl:.2f}[/green]",
        f"[green]+{roi:.0%}[/green]",
    )

    # NO wins scenario
    payout = 0
    pnl = -buy_amount
    roi = -1

    table.add_row(
        "[red]NO Wins[/red]",
        f"{shares:.1f}",
        f"[red]$0.00[/red]",
        f"[red]-${buy_amount:.2f}[/red]",
        f"[red]-100%[/red]",
    )

    console.print(table)
    console.print()

    # Break-even analysis
    console.print("[bold]Break-Even Analysis:[/bold]")
    console.print()
    console.print(f"  For YES bet to break even, true probability must be >= {price:.1%}")
    console.print(f"  Expected Value at current price: ${(price * shares - buy_amount):+.2f}")
    console.print()

    # Price scenarios
    console.print("[bold]If price moves before resolution:[/bold]")
    console.print()

    price_scenarios = [
        (price + 0.10, "+10%"),
        (price + 0.05, "+5%"),
        (price - 0.05, "-5%"),
        (price - 0.10, "-10%"),
    ]

    for new_price, label in price_scenarios:
        if 0 < new_price < 1:
            sell_value = shares * new_price
            pnl = sell_value - buy_amount
            if pnl >= 0:
                console.print(f"  Price {label} to {new_price:.0%}: [green]+${pnl:.2f}[/green]")
            else:
                console.print(f"  Price {label} to {new_price:.0%}: [red]${pnl:.2f}[/red]")

    console.print()


def _analyze_portfolio_scenario(console: Console, config, db: Database, output_format: str):
    """Analyze scenarios for full portfolio"""
    positions = db.get_positions(status='open')

    if not positions:
        if output_format == 'json':
            print_json({'success': True, 'message': 'No open positions'})
        else:
            console.print("[yellow]No open positions to analyze.[/yellow]")
        return

    # Calculate portfolio impact for different scenarios
    scenarios = _calculate_portfolio_scenarios(positions)

    if output_format == 'json':
        print_json({
            'success': True,
            'positions': len(positions),
            'scenarios': scenarios,
        })
        return

    # Display
    console.print()
    console.print(Panel("[bold]Portfolio Scenario Analysis[/bold]", border_style="cyan"))
    console.print()

    console.print(f"[bold]Open Positions:[/bold] {len(positions)}")
    console.print()

    # Per-position scenarios
    console.print("[bold]Position Outcomes:[/bold]")
    console.print()

    pos_table = Table(show_header=True, header_style="bold cyan", box=None)
    pos_table.add_column("Market", max_width=30)
    pos_table.add_column("Side", width=6, justify="center")
    pos_table.add_column("If Wins", width=12, justify="right")
    pos_table.add_column("If Loses", width=12, justify="right")

    for pos_data in scenarios['positions']:
        pos_table.add_row(
            pos_data['title'][:28],
            pos_data['side'].upper(),
            f"[green]+${pos_data['if_wins']:.2f}[/green]",
            f"[red]${pos_data['if_loses']:.2f}[/red]",
        )

    console.print(pos_table)
    console.print()

    # Aggregate scenarios
    console.print("[bold]Aggregate Scenarios:[/bold]")
    console.print()

    agg_table = Table(show_header=True, header_style="bold cyan", box=None)
    agg_table.add_column("Scenario", width=25)
    agg_table.add_column("P&L", width=15, justify="right")
    agg_table.add_column("Description", width=30)

    # Best case
    best = scenarios['best_case']
    agg_table.add_row(
        "[green]Best Case[/green]",
        f"[green]+${best['pnl']:.2f}[/green]",
        "All positions win",
    )

    # Worst case
    worst = scenarios['worst_case']
    agg_table.add_row(
        "[red]Worst Case[/red]",
        f"[red]${worst['pnl']:.2f}[/red]",
        "All positions lose",
    )

    # Expected value
    ev = scenarios['expected']
    ev_color = "green" if ev['pnl'] >= 0 else "red"
    agg_table.add_row(
        "Expected Value",
        f"[{ev_color}]${ev['pnl']:+.2f}[/{ev_color}]",
        "Based on current prices",
    )

    console.print(agg_table)
    console.print()

    # Risk metrics
    console.print("[bold]Risk Summary:[/bold]")
    console.print()
    console.print(f"  Max potential gain: [green]+${best['pnl']:.2f}[/green]")
    console.print(f"  Max potential loss: [red]${worst['pnl']:.2f}[/red]")
    console.print(f"  Risk/Reward ratio:  {abs(worst['pnl']) / best['pnl']:.2f}:1" if best['pnl'] > 0 else "  Risk/Reward ratio:  N/A")
    console.print()


def _calculate_market_scenarios(price: float) -> dict:
    """Calculate scenarios for a single market"""
    return {
        'current_price': price,
        'yes_wins': {
            'payout_per_share': 1.0,
            'probability': price,
        },
        'no_wins': {
            'payout_per_share': 0.0,
            'probability': 1 - price,
        },
        'breakeven_probability': price,
    }


def _calculate_portfolio_scenarios(positions: list) -> dict:
    """Calculate scenarios for full portfolio"""
    position_data = []
    best_total = 0
    worst_total = 0
    expected_total = 0

    for pos in positions:
        entry = pos.get('entry_price', 0)
        shares = pos.get('shares', 0)
        side = pos.get('side', 'yes')
        title = pos.get('title', pos.get('market_id', 'Unknown'))

        if side == 'yes':
            cost = entry * shares
            if_wins = shares - cost  # Get $1 per share, minus cost
            if_loses = -cost  # Lose entire cost
            # Estimate probability from entry price
            prob_win = entry
        else:
            cost = (1 - entry) * shares
            if_wins = shares - cost
            if_loses = -cost
            prob_win = 1 - entry

        expected_pnl = prob_win * if_wins + (1 - prob_win) * if_loses

        position_data.append({
            'title': title,
            'side': side,
            'cost': cost,
            'if_wins': if_wins,
            'if_loses': if_loses,
            'expected': expected_pnl,
        })

        best_total += if_wins
        worst_total += if_loses
        expected_total += expected_pnl

    return {
        'positions': position_data,
        'best_case': {
            'pnl': best_total,
            'description': 'All positions win',
        },
        'worst_case': {
            'pnl': worst_total,
            'description': 'All positions lose',
        },
        'expected': {
            'pnl': expected_total,
            'description': 'Probability-weighted expectation',
        },
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
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)
