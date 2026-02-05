"""Position simulator - Calculate potential P&L for prediction market positions"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, Confirm


@click.command()
@click.option("--market", "-m", default=None, help="Market ID or name (optional)")
@click.option("--price", "-p", type=float, default=None, help="Entry price (0.01-0.99)")
@click.option("--amount", "-a", type=float, default=None, help="Amount to invest in USD")
@click.option("--side", "-s", type=click.Choice(["yes", "no"]), default=None, help="Position side (yes/no)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with prompts")
def simulate(market, price, amount, side, interactive):
    """Simulate a prediction market position

    Calculate potential profit/loss before placing a trade.
    Great for understanding how prediction markets work!

    Examples:
        polyterm simulate --price 0.65 --amount 100 --side yes
        polyterm simulate -i   # Interactive mode
    """
    console = Console()

    console.print(Panel(
        "[bold]Position Simulator[/bold]\n"
        "[dim]Calculate your potential profit/loss before trading[/dim]",
        style="cyan"
    ))
    console.print()

    # Interactive mode or missing params
    if interactive or price is None or amount is None or side is None:
        price, amount, side = _get_interactive_inputs(console, price, amount, side)

    if price is None or amount is None or side is None:
        console.print("[red]Missing required parameters. Use --help for usage.[/red]")
        return

    # Validate inputs
    if not 0.01 <= price <= 0.99:
        console.print("[red]Price must be between 0.01 and 0.99[/red]")
        return

    if amount <= 0:
        console.print("[red]Amount must be positive[/red]")
        return

    # Calculate position metrics
    _display_simulation(console, market, price, amount, side)


def _get_interactive_inputs(console: Console, price, amount, side):
    """Get inputs interactively"""
    console.print("[cyan]Let's simulate a position![/cyan]")
    console.print()

    # Explain the concept
    console.print("[dim]In prediction markets:[/dim]")
    console.print("[dim]  - Price = Probability (e.g., $0.65 = 65% chance)[/dim]")
    console.print("[dim]  - If you're right, you get $1.00 per share[/dim]")
    console.print("[dim]  - If you're wrong, you lose your investment[/dim]")
    console.print()

    try:
        if side is None:
            console.print("[bold]What outcome do you want to bet on?[/bold]")
            console.print("  YES = You think the event WILL happen")
            console.print("  NO  = You think the event will NOT happen")
            side_input = Prompt.ask("[cyan]Side[/cyan]", choices=["yes", "no"], default="yes")
            side = side_input.lower()

        if price is None:
            console.print()
            console.print("[bold]What's the current price?[/bold]")
            console.print("[dim]Enter a value between 0.01 and 0.99 (e.g., 0.65 for 65%)[/dim]")
            price = FloatPrompt.ask("[cyan]Price[/cyan]", default=0.50)
            if not 0.01 <= price <= 0.99:
                console.print("[red]Price must be between 0.01 and 0.99[/red]")
                return None, None, None

        if amount is None:
            console.print()
            console.print("[bold]How much do you want to invest (in USD)?[/bold]")
            amount = FloatPrompt.ask("[cyan]Amount ($)[/cyan]", default=100.0)
            if amount <= 0:
                console.print("[red]Amount must be positive[/red]")
                return None, None, None

        return price, amount, side

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return None, None, None


def _display_simulation(console: Console, market: str, price: float, amount: float, side: str):
    """Display the simulation results"""

    # Calculate metrics
    shares = amount / price
    implied_prob = price * 100

    # If YES position
    if side == "yes":
        max_profit = shares * (1.0 - price)  # Win: get $1, paid $price
        max_loss = amount  # Lose: lose entire investment
        breakeven = price  # Need price at or above entry to not lose
        win_payout = shares * 1.0
    else:  # NO position
        # NO shares cost (1 - YES_price) and pay $1 if event doesn't happen
        no_price = 1.0 - price
        shares = amount / no_price
        max_profit = shares * price  # Win: get $1, paid $(1-price)
        max_loss = amount
        breakeven = no_price
        win_payout = shares * 1.0
        implied_prob = (1 - price) * 100  # NO implied probability

    # Fee calculation (2% on winnings)
    fee_rate = 0.02
    max_profit_after_fees = max_profit * (1 - fee_rate)

    # ROI calculation
    roi = (max_profit / amount) * 100
    roi_after_fees = (max_profit_after_fees / amount) * 100

    # Display header
    if market:
        console.print(f"[bold]Market:[/bold] {market}")
        console.print()

    # Position summary
    console.print("[bold yellow]Position Summary[/bold yellow]")
    summary = Table(show_header=False, box=None, padding=(0, 2))
    summary.add_column(style="cyan", width=20)
    summary.add_column(style="white")

    summary.add_row("Side", f"[bold]{'YES' if side == 'yes' else 'NO'}[/bold]")
    summary.add_row("Entry Price", f"${price:.2f}")
    summary.add_row("Investment", f"${amount:,.2f}")
    summary.add_row("Shares", f"{shares:,.2f}")
    summary.add_row("Implied Probability", f"{implied_prob:.1f}%")

    console.print(summary)
    console.print()

    # Outcomes
    console.print("[bold yellow]Potential Outcomes[/bold yellow]")
    outcomes = Table(show_header=True, box=None, padding=(0, 2))
    outcomes.add_column("Scenario", style="bold")
    outcomes.add_column("Result", justify="right")
    outcomes.add_column("P&L", justify="right")
    outcomes.add_column("ROI", justify="right")

    # Win scenario
    outcomes.add_row(
        f"[green]You WIN[/green] (event {'happens' if side == 'yes' else 'does NOT happen'})",
        f"[green]${win_payout:,.2f}[/green]",
        f"[green]+${max_profit_after_fees:,.2f}[/green]",
        f"[green]+{roi_after_fees:.1f}%[/green]"
    )

    # Lose scenario
    outcomes.add_row(
        f"[red]You LOSE[/red] (event {'does NOT happen' if side == 'yes' else 'happens'})",
        f"[red]$0.00[/red]",
        f"[red]-${max_loss:,.2f}[/red]",
        f"[red]-100%[/red]"
    )

    console.print(outcomes)
    console.print()

    # Breakeven analysis
    console.print("[bold yellow]Breakeven Analysis[/bold yellow]")
    console.print(f"  Entry price: ${price:.2f} ({price*100:.1f}%)")
    console.print(f"  Breakeven: Market must resolve in your favor")
    console.print(f"  Fee: 2% on winnings (${max_profit * fee_rate:,.2f} if you win)")
    console.print()

    # Price scenarios
    console.print("[bold yellow]What-If Scenarios[/bold yellow]")
    console.print("[dim]If you sell before resolution at different prices:[/dim]")
    console.print()

    scenarios = Table(show_header=True)
    scenarios.add_column("Exit Price", justify="center")
    scenarios.add_column("Value", justify="right")
    scenarios.add_column("P&L", justify="right")
    scenarios.add_column("ROI", justify="right")

    # Calculate P&L at different exit prices
    exit_prices = [0.20, 0.40, 0.60, 0.80, 0.90, 0.95]

    for exit_price in exit_prices:
        if side == "yes":
            exit_value = shares * exit_price
        else:
            # For NO positions, value increases as YES price decreases
            exit_value = shares * (1.0 - exit_price)

        pnl = exit_value - amount
        pnl_pct = (pnl / amount) * 100

        pnl_style = "green" if pnl >= 0 else "red"
        pnl_sign = "+" if pnl >= 0 else ""

        scenarios.add_row(
            f"${exit_price:.2f}",
            f"${exit_value:,.2f}",
            f"[{pnl_style}]{pnl_sign}${pnl:,.2f}[/{pnl_style}]",
            f"[{pnl_style}]{pnl_sign}{pnl_pct:.1f}%[/{pnl_style}]"
        )

    console.print(scenarios)
    console.print()

    # Educational tips
    console.print("[bold yellow]Tips[/bold yellow]")
    tips = [
        "The lower the price, the higher potential ROI (but lower probability)",
        "You can sell your position anytime before resolution",
        "Polymarket charges 2% fee only on winnings",
        "Consider the implied probability - does your analysis support it?",
    ]

    for tip in tips:
        console.print(f"  [dim]{tip}[/dim]")

    console.print()
