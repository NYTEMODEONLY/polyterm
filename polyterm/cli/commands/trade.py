"""Quick Trade Calculator - All-in-one trade analysis"""

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
@click.option("--market", "-m", "search_term", default=None, help="Market to trade")
@click.option("--amount", "-a", type=float, default=100, help="Trade amount ($)")
@click.option("--side", "-s", type=click.Choice(["yes", "no"]), default="yes", help="Side to buy")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def trade(ctx, search_term, amount, side, interactive, output_format):
    """Quick trade calculator - analyze before you trade

    Shows everything you need to know before placing a trade:
    - Current price and spread
    - Estimated shares and avg fill price
    - Fees and total cost
    - Breakeven and profit scenarios
    - Risk/reward analysis

    Examples:
        polyterm trade -m "bitcoin" -a 500         # Analyze $500 YES trade
        polyterm trade -m "election" -s no -a 200  # $200 NO trade
        polyterm trade --interactive               # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        search_term = Prompt.ask("[cyan]Search for market[/cyan]", default="")
        if search_term:
            side = Prompt.ask("[cyan]Side[/cyan]", choices=["yes", "no"], default="yes")
            amount_str = Prompt.ask("[cyan]Amount ($)[/cyan]", default="100")
            try:
                amount = float(amount_str)
            except ValueError:
                amount = 100

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
            progress.add_task("Analyzing trade...", total=None)

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

            # Get prices
            yes_price = _get_yes_price(market)
            no_price = 1 - yes_price

            # Get order book for slippage
            clob_token = market.get('clobTokenIds', [''])[0] if market.get('clobTokenIds') else ''
            orderbook = clob_client.get_orderbook(clob_token) if clob_token else None

            # Calculate trade
            trade_analysis = _analyze_trade(
                amount=amount,
                side=side,
                yes_price=yes_price,
                orderbook=orderbook,
            )

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'trade': {
                    'side': side,
                    'amount': amount,
                    'yes_price': yes_price,
                    'no_price': no_price,
                },
                'analysis': trade_analysis,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
        console.print()

        # Market info
        console.print("[bold]Market Info:[/bold]")
        console.print(f"  YES Price: [green]{yes_price:.2f}[/green] ({yes_price:.0%})")
        console.print(f"  NO Price: [red]{no_price:.2f}[/red] ({no_price:.0%})")
        if trade_analysis.get('spread'):
            console.print(f"  Spread: {trade_analysis['spread']:.2%}")
        console.print()

        # Trade summary box
        side_color = "green" if side == "yes" else "red"
        console.print(Panel(
            f"[bold {side_color}]BUY {side.upper()}[/bold {side_color}] - ${amount:,.2f}",
            border_style=side_color,
        ))
        console.print()

        # Execution details
        console.print("[bold]Execution Details:[/bold]")
        exec_table = Table(show_header=False, box=None, padding=(0, 2))
        exec_table.add_column(width=20)
        exec_table.add_column(justify="right")

        entry_price = trade_analysis['entry_price']
        shares = trade_analysis['shares']
        slippage = trade_analysis['slippage']

        exec_table.add_row("Entry Price", f"{entry_price:.4f}")
        exec_table.add_row("Estimated Shares", f"{shares:,.2f}")
        exec_table.add_row("Slippage", f"[yellow]{slippage:.2%}[/yellow]" if slippage > 0.01 else f"{slippage:.2%}")

        console.print(exec_table)
        console.print()

        # Cost breakdown
        console.print("[bold]Cost Breakdown:[/bold]")
        cost_table = Table(show_header=False, box=None, padding=(0, 2))
        cost_table.add_column(width=20)
        cost_table.add_column(justify="right")

        cost_table.add_row("Trade Amount", f"${amount:,.2f}")
        cost_table.add_row("Est. Fees (2% taker)", f"[yellow]-${trade_analysis['estimated_fees']:,.2f}[/yellow]")
        cost_table.add_row("Slippage Cost", f"[yellow]-${trade_analysis['slippage_cost']:,.2f}[/yellow]")
        cost_table.add_row("[bold]Total Cost[/bold]", f"[bold]${trade_analysis['total_cost']:,.2f}[/bold]")

        console.print(cost_table)
        console.print()

        # Profit scenarios
        console.print("[bold]Profit Scenarios:[/bold]")
        profit_table = Table(show_header=True, header_style="bold cyan", box=None)
        profit_table.add_column("Outcome", width=20)
        profit_table.add_column("Payout", width=12, justify="right")
        profit_table.add_column("Profit/Loss", width=12, justify="right")
        profit_table.add_column("ROI", width=10, justify="right")

        for scenario in trade_analysis['scenarios']:
            pnl_color = "green" if scenario['pnl'] > 0 else "red" if scenario['pnl'] < 0 else "yellow"
            profit_table.add_row(
                scenario['outcome'],
                f"${scenario['payout']:,.2f}",
                f"[{pnl_color}]${scenario['pnl']:+,.2f}[/{pnl_color}]",
                f"[{pnl_color}]{scenario['roi']:+.1%}[/{pnl_color}]",
            )

        console.print(profit_table)
        console.print()

        # Breakeven analysis
        console.print("[bold]Breakeven Analysis:[/bold]")
        console.print(f"  Breakeven Price: {trade_analysis['breakeven']:.4f} ({trade_analysis['breakeven']:.1%})")
        console.print(f"  Implied Probability: {entry_price:.1%}")
        console.print(f"  Edge Needed: {trade_analysis['edge_needed']:.1%} over market")
        console.print()

        # Risk metrics
        console.print("[bold]Risk Metrics:[/bold]")
        risk_table = Table(show_header=False, box=None, padding=(0, 2))
        risk_table.add_column(width=20)
        risk_table.add_column(justify="right")

        risk_table.add_row("Max Profit", f"[green]+${trade_analysis['max_profit']:,.2f}[/green]")
        risk_table.add_row("Max Loss", f"[red]-${trade_analysis['max_loss']:,.2f}[/red]")
        risk_table.add_row("Risk/Reward", f"{trade_analysis['risk_reward']:.2f}:1")
        risk_table.add_row("Expected Value*", f"[{'green' if trade_analysis['expected_value'] >= 0 else 'red'}]${trade_analysis['expected_value']:+,.2f}[/{'green' if trade_analysis['expected_value'] >= 0 else 'red'}]")

        console.print(risk_table)
        console.print()
        console.print("[dim]*EV assumes market price = true probability[/dim]")
        console.print()

        # Recommendation
        _display_recommendation(console, trade_analysis, entry_price)

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()


def _get_yes_price(market: dict) -> float:
    """Get YES price from market data"""
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


def _analyze_trade(amount: float, side: str, yes_price: float, orderbook: dict) -> dict:
    """Analyze a potential trade"""
    # Determine entry price based on side
    if side == "yes":
        entry_price = yes_price
        win_payout = 1.0
        lose_payout = 0.0
    else:
        entry_price = 1 - yes_price
        win_payout = 1.0
        lose_payout = 0.0

    # Calculate slippage from orderbook
    spread = 0
    slippage = 0
    slippage_cost = 0

    if orderbook:
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if bids and asks:
            try:
                best_bid = float(bids[0].get('price', 0))
                best_ask = float(asks[0].get('price', 0))
                spread = best_ask - best_bid

                # Estimate slippage based on order book depth
                if side == "yes":
                    # Buying YES means lifting asks
                    slippage = _estimate_slippage(asks, amount)
                else:
                    # Buying NO means lifting asks on NO side (or hitting bids on YES)
                    slippage = _estimate_slippage(bids, amount)

                slippage_cost = slippage * amount
                entry_price = entry_price * (1 + slippage)
            except (ValueError, IndexError):
                pass

    # Calculate shares
    shares = amount / entry_price if entry_price > 0 else 0

    # Fees (Polymarket: 0% maker, ~2% taker on profits)
    # Simplified: estimate 2% on winning trades
    estimated_fees = amount * 0.02

    # Total cost
    total_cost = amount + slippage_cost

    # Profit scenarios
    scenarios = []

    # Win scenario
    win_payout_total = shares * win_payout
    win_pnl = win_payout_total - total_cost - (win_payout_total - total_cost) * 0.02  # Fee on profit
    win_roi = win_pnl / total_cost if total_cost > 0 else 0

    scenarios.append({
        'outcome': f'{side.upper()} wins',
        'payout': win_payout_total,
        'pnl': win_pnl,
        'roi': win_roi,
    })

    # Lose scenario
    lose_payout_total = shares * lose_payout
    lose_pnl = lose_payout_total - total_cost
    lose_roi = lose_pnl / total_cost if total_cost > 0 else 0

    scenarios.append({
        'outcome': f'{side.upper()} loses',
        'payout': lose_payout_total,
        'pnl': lose_pnl,
        'roi': lose_roi,
    })

    # Breakeven (accounting for fees)
    breakeven = entry_price * 1.02  # Need 2% more to cover fees

    # Risk metrics
    max_profit = win_pnl
    max_loss = abs(lose_pnl)
    risk_reward = max_profit / max_loss if max_loss > 0 else float('inf')

    # Expected value (assuming market price = true probability)
    prob = entry_price if side == "yes" else (1 - entry_price)
    expected_value = (prob * win_pnl) + ((1 - prob) * lose_pnl)

    # Edge needed
    edge_needed = entry_price * 0.02  # Need to beat market by fee amount

    return {
        'entry_price': entry_price,
        'shares': shares,
        'slippage': slippage,
        'slippage_cost': slippage_cost,
        'spread': spread,
        'estimated_fees': estimated_fees,
        'total_cost': total_cost,
        'scenarios': scenarios,
        'breakeven': breakeven,
        'max_profit': max_profit,
        'max_loss': max_loss,
        'risk_reward': risk_reward,
        'expected_value': expected_value,
        'edge_needed': edge_needed,
    }


def _estimate_slippage(orders: list, amount: float) -> float:
    """Estimate slippage from order book"""
    if not orders or amount <= 0:
        return 0

    total_available = 0
    for order in orders[:10]:  # Check top 10 levels
        try:
            price = float(order.get('price', 0))
            size = float(order.get('size', 0))
            total_available += price * size
        except (ValueError, TypeError):
            continue

    if total_available <= 0:
        return 0.05  # Assume 5% slippage if no data

    # Slippage increases as trade size approaches available liquidity
    utilization = amount / total_available
    if utilization < 0.1:
        return 0.001  # 0.1% for small trades
    elif utilization < 0.3:
        return 0.005  # 0.5%
    elif utilization < 0.5:
        return 0.01  # 1%
    elif utilization < 0.8:
        return 0.02  # 2%
    else:
        return 0.05  # 5% for large trades


def _display_recommendation(console: Console, analysis: dict, entry_price: float):
    """Display trade recommendation"""
    console.print("[bold]Quick Assessment:[/bold]")

    issues = []
    positives = []

    # Check slippage
    if analysis['slippage'] > 0.02:
        issues.append("High slippage - consider smaller size or limit order")
    elif analysis['slippage'] < 0.005:
        positives.append("Low slippage")

    # Check risk/reward
    if analysis['risk_reward'] > 1.5:
        positives.append(f"Good risk/reward ({analysis['risk_reward']:.1f}:1)")
    elif analysis['risk_reward'] < 0.5:
        issues.append(f"Poor risk/reward ({analysis['risk_reward']:.1f}:1)")

    # Check price extremes
    if entry_price > 0.90:
        issues.append("Price very high - limited upside")
    elif entry_price < 0.10:
        issues.append("Price very low - could be illiquid")

    # Check fees impact
    fee_impact = analysis['estimated_fees'] / analysis['total_cost'] if analysis['total_cost'] > 0 else 0
    if fee_impact > 0.03:
        issues.append("Fees are significant relative to trade size")

    console.print()
    for pos in positives:
        console.print(f"  [green]+[/green] {pos}")
    for issue in issues:
        console.print(f"  [yellow]![/yellow] {issue}")

    if not issues and not positives:
        console.print("  [dim]Trade looks reasonable[/dim]")

    console.print()
