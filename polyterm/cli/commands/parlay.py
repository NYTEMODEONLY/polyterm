"""Parlay Calculator - Combine multiple bets"""

import click
from typing import List, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, Confirm

from ...utils.json_output import print_json


@click.command()
@click.option("--markets", "-m", default=None, help="Comma-separated probabilities (e.g., '0.65,0.70,0.80')")
@click.option("--amount", "-a", type=float, default=None, help="Bet amount in USD")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def parlay(markets, amount, interactive, output_format):
    """Calculate combined odds for multi-leg parlays

    A parlay combines multiple bets - all must win for you to profit.
    Higher risk, higher reward!

    Examples:
        polyterm parlay --markets "0.65,0.70,0.80" --amount 100
        polyterm parlay -i   # Interactive mode
    """
    console = Console()

    if interactive or (markets is None and amount is None):
        probs, amount = _interactive_mode(console)
        if probs is None:
            return
    else:
        if markets is None:
            console.print("[red]Please provide market probabilities with --markets[/red]")
            return
        try:
            probs = [float(p.strip()) for p in markets.split(',')]
        except ValueError:
            console.print("[red]Invalid probability format. Use comma-separated decimals.[/red]")
            return

        if amount is None:
            amount = 100.0

    # Validate
    for p in probs:
        if not 0.01 <= p <= 0.99:
            console.print(f"[red]Probability {p} must be between 0.01 and 0.99[/red]")
            return

    if len(probs) < 2:
        console.print("[red]A parlay needs at least 2 legs.[/red]")
        return

    if len(probs) > 10:
        console.print("[red]Maximum 10 legs in a parlay.[/red]")
        return

    # Calculate parlay
    result = _calculate_parlay(probs, amount)

    if output_format == 'json':
        print_json({
            'success': True,
            'legs': len(probs),
            'probabilities': probs,
            'amount': amount,
            **result,
        })
    else:
        _display_result(console, probs, amount, result)


def _interactive_mode(console: Console) -> Tuple[List[float], float]:
    """Interactive parlay builder"""
    console.print(Panel(
        "[bold]Parlay Calculator[/bold]\n"
        "[dim]Combine multiple bets for higher potential payouts[/dim]",
        style="cyan"
    ))
    console.print()

    console.print("[bold yellow]What is a parlay?[/bold yellow]")
    console.print("A parlay combines multiple bets into one. ALL legs must win for you to profit.")
    console.print("The more legs, the higher the potential payout - but lower chance of winning.")
    console.print()

    probs = []
    console.print("[bold]Enter the probability for each leg (or 'done' when finished):[/bold]")
    console.print("[dim]Enter as decimal (0.65) or percentage (65)[/dim]")
    console.print()

    while len(probs) < 10:
        try:
            prompt = f"[cyan]Leg {len(probs) + 1} probability[/cyan]"
            if probs:
                prompt += " [dim](or 'done')[/dim]"

            val = Prompt.ask(prompt)

            if val.lower() == 'done' and probs:
                break

            if val.lower() == 'done' and not probs:
                console.print("[yellow]Need at least one leg![/yellow]")
                continue

            # Parse probability
            prob = float(val)
            if prob > 1:
                prob = prob / 100  # Convert percentage to decimal

            if not 0.01 <= prob <= 0.99:
                console.print("[yellow]Probability must be between 1% and 99%[/yellow]")
                continue

            probs.append(prob)
            console.print(f"  [green]Added: {prob*100:.0f}% probability[/green]")

            if len(probs) >= 2:
                # Show running total
                combined = 1.0
                for p in probs:
                    combined *= p
                console.print(f"  [dim]Current combined probability: {combined*100:.1f}%[/dim]")

        except ValueError:
            console.print("[yellow]Invalid input. Enter a decimal or type 'done'.[/yellow]")
        except (KeyboardInterrupt, EOFError):
            console.print("\n[yellow]Cancelled.[/yellow]")
            return None, None

    if len(probs) < 2:
        console.print("[red]A parlay needs at least 2 legs.[/red]")
        return None, None

    console.print()
    amount = FloatPrompt.ask("[cyan]Bet amount ($)[/cyan]", default=100.0)

    return probs, amount


def _calculate_parlay(probs: List[float], amount: float) -> dict:
    """Calculate parlay metrics"""

    # Combined probability
    combined_prob = 1.0
    for p in probs:
        combined_prob *= p

    # Implied odds (American format)
    if combined_prob >= 0.5:
        american_odds = -(combined_prob / (1 - combined_prob)) * 100
    else:
        american_odds = ((1 - combined_prob) / combined_prob) * 100

    # Decimal odds
    decimal_odds = 1 / combined_prob

    # Potential payout and profit
    potential_payout = amount * decimal_odds
    potential_profit = potential_payout - amount

    # ROI if all legs hit
    roi = (potential_profit / amount) * 100

    # Fee-adjusted (2% on winnings)
    fee_rate = 0.02
    profit_after_fees = potential_profit * (1 - fee_rate)
    payout_after_fees = amount + profit_after_fees

    # Risk assessment
    if combined_prob >= 0.25:
        risk_level = "Moderate"
    elif combined_prob >= 0.10:
        risk_level = "High"
    elif combined_prob >= 0.05:
        risk_level = "Very High"
    else:
        risk_level = "Extreme"

    return {
        'combined_probability': combined_prob,
        'decimal_odds': decimal_odds,
        'american_odds': american_odds,
        'potential_payout': potential_payout,
        'potential_profit': potential_profit,
        'profit_after_fees': profit_after_fees,
        'payout_after_fees': payout_after_fees,
        'roi': roi,
        'risk_level': risk_level,
    }


def _display_result(console: Console, probs: List[float], amount: float, result: dict):
    """Display parlay calculation results"""

    console.print()

    # Legs breakdown
    console.print("[bold yellow]Parlay Legs[/bold yellow]")
    legs_table = Table(show_header=True, box=None)
    legs_table.add_column("Leg", style="cyan", justify="center", width=5)
    legs_table.add_column("Probability", justify="center")
    legs_table.add_column("Decimal Odds", justify="center")

    for i, p in enumerate(probs, 1):
        odds = 1 / p
        legs_table.add_row(
            str(i),
            f"{p*100:.0f}%",
            f"{odds:.2f}x",
        )

    console.print(legs_table)
    console.print()

    # Combined results
    combined_prob = result['combined_probability']

    # Color code risk
    if combined_prob >= 0.25:
        prob_color = "green"
    elif combined_prob >= 0.10:
        prob_color = "yellow"
    elif combined_prob >= 0.05:
        prob_color = "orange1"
    else:
        prob_color = "red"

    console.print("[bold yellow]Combined Results[/bold yellow]")
    console.print()

    results_table = Table(show_header=False, box=None, padding=(0, 2))
    results_table.add_column(style="cyan", width=22)
    results_table.add_column(style="white")

    results_table.add_row("Legs", str(len(probs)))
    results_table.add_row("Bet Amount", f"${amount:,.2f}")
    results_table.add_row(
        "Combined Probability",
        f"[{prob_color}]{combined_prob*100:.2f}%[/{prob_color}]"
    )
    results_table.add_row("Decimal Odds", f"{result['decimal_odds']:.2f}x")
    results_table.add_row("Risk Level", f"[{prob_color}]{result['risk_level']}[/{prob_color}]")

    console.print(results_table)
    console.print()

    # Payouts
    console.print("[bold yellow]Potential Payouts[/bold yellow]")
    console.print()

    payout_table = Table(show_header=True)
    payout_table.add_column("Scenario", style="bold")
    payout_table.add_column("Payout", justify="right")
    payout_table.add_column("Profit", justify="right")
    payout_table.add_column("ROI", justify="right")

    payout_table.add_row(
        "[green]ALL legs win[/green]",
        f"[green]${result['payout_after_fees']:,.2f}[/green]",
        f"[green]+${result['profit_after_fees']:,.2f}[/green]",
        f"[green]+{result['roi']*(1-0.02):.0f}%[/green]",
    )
    payout_table.add_row(
        "[red]ANY leg loses[/red]",
        f"[red]$0.00[/red]",
        f"[red]-${amount:,.2f}[/red]",
        f"[red]-100%[/red]",
    )

    console.print(payout_table)
    console.print()

    # Expected value
    ev = (combined_prob * result['profit_after_fees']) - ((1 - combined_prob) * amount)
    ev_sign = "+" if ev >= 0 else ""
    ev_color = "green" if ev >= 0 else "red"

    console.print("[bold yellow]Expected Value[/bold yellow]")
    console.print(f"  EV: [{ev_color}]{ev_sign}${ev:,.2f}[/{ev_color}] per bet")
    console.print()

    # Warnings
    if combined_prob < 0.10:
        console.print("[bold red]Warning[/bold red]")
        console.print(f"  [red]This parlay has only a {combined_prob*100:.1f}% chance of winning.[/red]")
        console.print("  [dim]Consider reducing the number of legs or finding higher-probability bets.[/dim]")
        console.print()

    # Tips
    console.print("[dim]Tips:[/dim]")
    console.print("[dim]  - Parlays are high-risk, high-reward bets[/dim]")
    console.print("[dim]  - Each additional leg significantly reduces win probability[/dim]")
    console.print("[dim]  - Consider the expected value, not just potential payout[/dim]")
