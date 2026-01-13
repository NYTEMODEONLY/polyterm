"""Fee Calculator - Calculate trading fees and slippage"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


# Polymarket fee structure (as of 2024)
MAKER_FEE = 0.0  # Makers pay no fees
TAKER_FEE = 0.02  # 2% on winnings (not on principal)
MATIC_GAS_ESTIMATE = 0.01  # Approximate gas in MATIC


@click.command()
@click.option("--amount", "-a", type=float, default=None, help="Trade amount in USD")
@click.option("--price", "-p", type=float, default=None, help="Market price (0.01-0.99)")
@click.option("--market", "-m", default=None, help="Market ID or search term (for slippage)")
@click.option("--side", "-s", type=click.Choice(["buy", "sell"]), default="buy", help="Trade side")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def fees(ctx, amount, price, market, side, interactive, output_format):
    """Calculate trading fees and slippage

    Understand the true cost of your trades including:
    - Platform fees (2% on winnings)
    - Estimated slippage based on order book
    - Gas fees for on-chain transactions

    Examples:
        polyterm fees --amount 100 --price 0.65
        polyterm fees -a 1000 -p 0.50 --market "bitcoin"
        polyterm fees -i   # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive or (amount is None and price is None):
        result = _interactive_mode(console, config)
        if result is None:
            return
        amount, price, market, side = result

    # Validate inputs
    if amount is None or amount <= 0:
        console.print("[red]Please provide a valid trade amount (> 0)[/red]")
        return

    if price is None or not 0.01 <= price <= 0.99:
        console.print("[red]Please provide a valid price (0.01-0.99)[/red]")
        return

    # Calculate fees
    result = _calculate_fees(amount, price, side)

    # Get slippage estimate if market specified
    slippage_info = None
    if market:
        slippage_info = _estimate_slippage(console, config, market, amount, price, side)

    if output_format == 'json':
        output = {
            'success': True,
            'inputs': {
                'amount': amount,
                'price': price,
                'side': side,
            },
            **result,
        }
        if slippage_info:
            output['slippage'] = slippage_info
        print_json(output)
    else:
        _display_results(console, amount, price, side, result, slippage_info)


def _interactive_mode(console: Console, config):
    """Interactive fee calculation"""
    console.print(Panel(
        "[bold]Fee & Slippage Calculator[/bold]\n\n"
        "[dim]Calculate the true cost of your trades.[/dim]\n\n"
        "[bold]Polymarket Fees:[/bold]\n"
        "  - Makers: [green]0%[/green] (limit orders that add liquidity)\n"
        "  - Takers: [yellow]2%[/yellow] on winnings (market orders)\n"
        "  - Gas: ~$0.01 per transaction (Polygon)",
        title="[cyan]Fee Calculator[/cyan]",
        border_style="cyan",
    ))
    console.print()

    try:
        # Get trade amount
        console.print("[bold]Trade Amount[/bold]")
        console.print("[dim]How much do you want to trade?[/dim]")
        amount = FloatPrompt.ask("[cyan]Amount (USD)[/cyan]", default=100.0)
        console.print()

        # Get price
        console.print("[bold]Market Price[/bold]")
        console.print("[dim]Current YES price (or your limit price)[/dim]")
        price_input = FloatPrompt.ask("[cyan]Price (e.g., 65 for 65%)[/cyan]", default=50.0)
        price = price_input / 100 if price_input > 1 else price_input
        console.print()

        # Get side
        console.print("[bold]Trade Side[/bold]")
        side = Prompt.ask(
            "[cyan]Buy or Sell?[/cyan]",
            choices=["buy", "sell"],
            default="buy"
        )
        console.print()

        # Optional: specific market for slippage
        console.print("[bold]Market (optional)[/bold]")
        console.print("[dim]Enter market ID/name for slippage estimate[/dim]")
        market = Prompt.ask("[cyan]Market[/cyan]", default="")
        if not market:
            market = None
        console.print()

        return amount, price, market, side

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return None


def _calculate_fees(amount: float, price: float, side: str) -> dict:
    """Calculate fees for a trade"""

    # Shares purchased
    shares = amount / price

    # Potential outcomes
    if side == "buy":
        # Buying YES shares
        payout_if_win = shares * 1.0  # Each share pays $1 if YES wins
        gross_profit = payout_if_win - amount

        # Taker fee (2% on winnings, not on return of principal)
        if gross_profit > 0:
            taker_fee = gross_profit * TAKER_FEE
        else:
            taker_fee = 0

        net_profit = gross_profit - taker_fee
        loss_if_no = amount  # Lose entire investment

        roi_if_win = (net_profit / amount) * 100 if amount > 0 else 0

    else:
        # Selling YES shares (buying NO)
        # NO shares cost (1 - price) each
        no_price = 1 - price
        no_shares = amount / no_price
        payout_if_win = no_shares * 1.0  # Each NO share pays $1 if NO wins
        gross_profit = payout_if_win - amount

        if gross_profit > 0:
            taker_fee = gross_profit * TAKER_FEE
        else:
            taker_fee = 0

        net_profit = gross_profit - taker_fee
        loss_if_no = amount

        roi_if_win = (net_profit / amount) * 100 if amount > 0 else 0
        shares = no_shares

    # Gas estimate (Polygon is cheap)
    gas_estimate = MATIC_GAS_ESTIMATE

    # Breakeven price (what price do you need to sell at to break even)
    # For a buy: breakeven = cost / shares
    # But need to account for fees on profit
    # breakeven = amount / shares after fees
    # This is simplified - actual breakeven depends on when you exit

    return {
        'shares': shares,
        'gross_profit_if_win': gross_profit,
        'taker_fee': taker_fee,
        'net_profit_if_win': net_profit,
        'loss_if_wrong': loss_if_no,
        'roi_if_win': roi_if_win,
        'gas_estimate': gas_estimate,
        'maker_fee': 0.0,
        'effective_fee_rate': (taker_fee / gross_profit * 100) if gross_profit > 0 else 0,
    }


def _estimate_slippage(console: Console, config, market: str, amount: float, price: float, side: str) -> dict:
    """Estimate slippage from order book"""

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Search for market
        markets = gamma_client.search_markets(market, limit=1)
        if not markets:
            return {'error': f'Market not found: {market}'}

        selected = markets[0]
        market_id = selected.get('id', selected.get('condition_id', ''))

        # Try to get order book
        clob_client = CLOBClient()
        try:
            # Get token IDs from market
            tokens = selected.get('tokens', [])
            if not tokens:
                return {'error': 'No token data available'}

            # Get YES token ID
            yes_token = None
            for token in tokens:
                if token.get('outcome', '').lower() == 'yes':
                    yes_token = token.get('token_id')
                    break

            if not yes_token:
                return {'error': 'Could not find YES token'}

            orderbook = clob_client.get_orderbook(yes_token)

            if not orderbook:
                return {'error': 'Order book not available'}

            # Calculate slippage
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            if side == 'buy':
                # Buying - we take from asks
                orders = sorted(asks, key=lambda x: float(x.get('price', 0)))
            else:
                # Selling - we take from bids
                orders = sorted(bids, key=lambda x: float(x.get('price', 0)), reverse=True)

            if not orders:
                return {'error': 'No orders on this side of book'}

            # Simulate order fill
            remaining = amount
            total_cost = 0
            total_shares = 0
            fills = []

            for order in orders:
                order_price = float(order.get('price', 0))
                order_size = float(order.get('size', 0))
                order_value = order_price * order_size

                if remaining <= 0:
                    break

                fill_amount = min(remaining, order_value)
                fill_shares = fill_amount / order_price

                total_cost += fill_amount
                total_shares += fill_shares
                remaining -= fill_amount

                fills.append({
                    'price': order_price,
                    'shares': fill_shares,
                    'cost': fill_amount,
                })

            if total_shares == 0:
                return {'error': 'Insufficient liquidity'}

            avg_price = total_cost / total_shares
            slippage_pct = abs(avg_price - price) / price * 100 if price > 0 else 0

            return {
                'market_id': market_id,
                'best_price': float(orders[0].get('price', 0)) if orders else 0,
                'avg_fill_price': avg_price,
                'slippage_percent': slippage_pct,
                'fills': len(fills),
                'unfilled': remaining,
                'sufficient_liquidity': remaining == 0,
            }

        except Exception as e:
            return {'error': f'Order book error: {str(e)}'}
        finally:
            clob_client.close()

    except Exception as e:
        return {'error': str(e)}
    finally:
        gamma_client.close()


def _display_results(console: Console, amount: float, price: float, side: str, result: dict, slippage: dict = None):
    """Display fee calculation results"""
    console.print()

    side_display = "Buying YES" if side == "buy" else "Buying NO"
    console.print(Panel(
        f"[bold]Trade Analysis: {side_display}[/bold]",
        border_style="cyan",
    ))
    console.print()

    # Input summary
    console.print("[bold yellow]Trade Details[/bold yellow]")
    console.print(f"  Amount: [cyan]${amount:,.2f}[/cyan]")
    console.print(f"  Price: [cyan]{price * 100:.1f}%[/cyan]")
    console.print(f"  Shares: [cyan]{result['shares']:,.2f}[/cyan]")
    console.print()

    # Fee breakdown
    console.print("[bold yellow]Fee Breakdown[/bold yellow]")

    fee_table = Table(show_header=True, header_style="bold", box=None)
    fee_table.add_column("Fee Type", style="cyan")
    fee_table.add_column("Amount", justify="right")
    fee_table.add_column("Notes", style="dim")

    fee_table.add_row(
        "Maker Fee",
        f"$0.00",
        "0% for limit orders"
    )
    fee_table.add_row(
        "Taker Fee",
        f"${result['taker_fee']:,.2f}",
        "2% on winnings only"
    )
    fee_table.add_row(
        "Gas (est.)",
        f"${result['gas_estimate']:.2f}",
        "Polygon network"
    )
    fee_table.add_row(
        "[bold]Total Fees[/bold]",
        f"[bold]${result['taker_fee'] + result['gas_estimate']:,.2f}[/bold]",
        ""
    )

    console.print(fee_table)
    console.print()

    # Outcomes
    console.print("[bold yellow]Potential Outcomes[/bold yellow]")

    outcome_table = Table(show_header=True, header_style="bold", box=None)
    outcome_table.add_column("Outcome", style="cyan")
    outcome_table.add_column("Result", justify="right")

    if side == "buy":
        outcome_table.add_row(
            "[green]If YES wins[/green]",
            f"[green]+${result['net_profit_if_win']:,.2f}[/green] ({result['roi_if_win']:.0f}% ROI)"
        )
        outcome_table.add_row(
            "[red]If NO wins[/red]",
            f"[red]-${result['loss_if_wrong']:,.2f}[/red] (-100%)"
        )
    else:
        outcome_table.add_row(
            "[green]If NO wins[/green]",
            f"[green]+${result['net_profit_if_win']:,.2f}[/green] ({result['roi_if_win']:.0f}% ROI)"
        )
        outcome_table.add_row(
            "[red]If YES wins[/red]",
            f"[red]-${result['loss_if_wrong']:,.2f}[/red] (-100%)"
        )

    console.print(outcome_table)
    console.print()

    # Slippage analysis
    if slippage:
        console.print("[bold yellow]Slippage Analysis[/bold yellow]")

        if 'error' in slippage:
            console.print(f"  [yellow]{slippage['error']}[/yellow]")
        else:
            slippage_color = "green" if slippage['slippage_percent'] < 1 else "yellow" if slippage['slippage_percent'] < 3 else "red"

            console.print(f"  Best price: [cyan]{slippage['best_price'] * 100:.1f}%[/cyan]")
            console.print(f"  Avg fill price: [cyan]{slippage['avg_fill_price'] * 100:.1f}%[/cyan]")
            console.print(f"  Slippage: [{slippage_color}]{slippage['slippage_percent']:.2f}%[/{slippage_color}]")
            console.print(f"  Order fills: {slippage['fills']}")

            if not slippage['sufficient_liquidity']:
                console.print(f"  [yellow]Warning: Only ${amount - slippage['unfilled']:,.2f} can be filled[/yellow]")

        console.print()

    # Tips
    console.print("[dim]Tips:[/dim]")
    console.print("[dim]  - Use limit orders (maker) to pay 0% fees[/dim]")
    console.print("[dim]  - Fees are only charged on profits, not on your stake[/dim]")
    console.print("[dim]  - Large orders may experience significant slippage[/dim]")
    console.print("[dim]  - Split large orders to minimize market impact[/dim]")
    console.print()
