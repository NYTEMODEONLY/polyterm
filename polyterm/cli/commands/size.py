"""Position Size Calculator - Optimal bet sizing"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt

from ...utils.json_output import print_json


@click.command()
@click.option("--bankroll", "-b", type=float, default=None, help="Your total bankroll/budget")
@click.option("--probability", "-p", type=float, default=None, help="Your estimated probability (0.01-0.99)")
@click.option("--odds", "-o", type=float, default=None, help="Market price/odds (0.01-0.99)")
@click.option("--kelly", "-k", type=float, default=0.25, help="Kelly fraction (default: 0.25 = quarter Kelly)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def size(bankroll, probability, odds, kelly, interactive, output_format):
    """Calculate optimal position size

    Uses Kelly Criterion and other strategies to recommend bet sizes
    based on your edge and bankroll.

    Examples:
        polyterm size --bankroll 1000 --probability 0.65 --odds 0.50
        polyterm size -i   # Interactive mode
    """
    console = Console()

    if interactive or (bankroll is None and probability is None and odds is None):
        result = _interactive_mode(console)
        if result is None:
            return
        bankroll, probability, odds, kelly = result

    # Validate inputs
    if bankroll is None or bankroll <= 0:
        console.print("[red]Please provide a valid bankroll (> 0)[/red]")
        return

    if probability is None or not 0.01 <= probability <= 0.99:
        console.print("[red]Please provide a valid probability (0.01-0.99)[/red]")
        return

    if odds is None or not 0.01 <= odds <= 0.99:
        console.print("[red]Please provide valid odds/market price (0.01-0.99)[/red]")
        return

    # Calculate position sizes
    result = _calculate_sizes(bankroll, probability, odds, kelly)

    if output_format == 'json':
        print_json({
            'success': True,
            'inputs': {
                'bankroll': bankroll,
                'probability': probability,
                'odds': odds,
                'kelly_fraction': kelly,
            },
            **result,
        })
    else:
        _display_results(console, bankroll, probability, odds, kelly, result)


def _interactive_mode(console: Console):
    """Interactive position sizing"""
    console.print(Panel(
        "[bold]Position Size Calculator[/bold]\n\n"
        "[dim]Determine optimal bet sizes using Kelly Criterion.[/dim]\n\n"
        "[yellow]Kelly Criterion[/yellow] calculates the optimal bet size\n"
        "to maximize long-term growth while managing risk.\n\n"
        "[dim]Most traders use 'fractional Kelly' (1/4 or 1/2) for safety.[/dim]",
        title="[cyan]Bet Sizing[/cyan]",
        border_style="cyan",
    ))
    console.print()

    try:
        # Get bankroll
        console.print("[bold]Step 1: Your Bankroll[/bold]")
        console.print("[dim]How much capital do you have to trade with?[/dim]")
        bankroll = FloatPrompt.ask("[cyan]Bankroll ($)[/cyan]", default=1000.0)
        console.print()

        # Get estimated probability
        console.print("[bold]Step 2: Your Estimated Probability[/bold]")
        console.print("[dim]What do YOU think the true probability is?[/dim]")
        console.print("[dim]Enter as decimal (0.65) or percentage (65)[/dim]")
        prob_input = FloatPrompt.ask("[cyan]Your estimated probability[/cyan]", default=0.6)
        probability = prob_input / 100 if prob_input > 1 else prob_input
        console.print()

        # Get market odds
        console.print("[bold]Step 3: Market Price[/bold]")
        console.print("[dim]What is the current market price for YES?[/dim]")
        console.print("[dim]Enter as decimal (0.50) or percentage (50)[/dim]")
        odds_input = FloatPrompt.ask("[cyan]Market price[/cyan]", default=0.5)
        odds = odds_input / 100 if odds_input > 1 else odds_input
        console.print()

        # Get Kelly fraction
        console.print("[bold]Step 4: Kelly Fraction[/bold]")
        console.print("[dim]How aggressive do you want to be?[/dim]")
        console.print("  [cyan]0.25[/cyan] = Quarter Kelly (conservative, recommended)")
        console.print("  [cyan]0.50[/cyan] = Half Kelly (moderate)")
        console.print("  [cyan]1.00[/cyan] = Full Kelly (aggressive)")
        kelly = FloatPrompt.ask("[cyan]Kelly fraction[/cyan]", default=0.25)
        console.print()

        return bankroll, probability, odds, kelly

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return None


def _calculate_sizes(bankroll: float, probability: float, odds: float, kelly_fraction: float) -> dict:
    """Calculate position sizes using various strategies"""

    # Calculate edge
    # Edge = P(win) * payout - P(loss) * stake
    # For binary markets: payout on YES = (1 - odds) / odds
    payout_ratio = (1 - odds) / odds  # How much you win per dollar risked

    # Expected value
    ev_per_dollar = (probability * payout_ratio) - (1 - probability)

    # Kelly Criterion: f* = (bp - q) / b
    # Where b = odds received on win, p = probability of win, q = probability of loss
    kelly_full = (probability * (1 + payout_ratio) - 1) / payout_ratio if payout_ratio > 0 else 0
    kelly_full = max(0, kelly_full)  # Can't be negative

    # Fractional Kelly
    kelly_bet = kelly_full * kelly_fraction

    # Calculate actual amounts
    full_kelly_amount = bankroll * kelly_full
    fractional_kelly_amount = bankroll * kelly_bet

    # Fixed percentage strategies
    fixed_1pct = bankroll * 0.01
    fixed_2pct = bankroll * 0.02
    fixed_5pct = bankroll * 0.05

    # Potential outcomes for fractional Kelly bet
    if fractional_kelly_amount > 0:
        shares_bought = fractional_kelly_amount / odds
        profit_if_win = shares_bought * (1 - odds)  # Each share pays $1, cost was odds
        loss_if_lose = fractional_kelly_amount
        roi_if_win = (profit_if_win / fractional_kelly_amount) * 100 if fractional_kelly_amount > 0 else 0
    else:
        shares_bought = 0
        profit_if_win = 0
        loss_if_lose = 0
        roi_if_win = 0

    # Has edge?
    has_edge = probability > odds

    return {
        'edge': {
            'has_edge': has_edge,
            'edge_pct': (probability - odds) * 100,
            'ev_per_dollar': ev_per_dollar,
        },
        'kelly': {
            'full_kelly_pct': kelly_full * 100,
            'full_kelly_amount': full_kelly_amount,
            'fractional_kelly_pct': kelly_bet * 100,
            'fractional_kelly_amount': fractional_kelly_amount,
        },
        'fixed': {
            'one_percent': fixed_1pct,
            'two_percent': fixed_2pct,
            'five_percent': fixed_5pct,
        },
        'outcomes': {
            'shares': shares_bought,
            'profit_if_win': profit_if_win,
            'loss_if_lose': loss_if_lose,
            'roi_if_win': roi_if_win,
        },
        'recommendation': _get_recommendation(has_edge, kelly_bet, fractional_kelly_amount),
    }


def _get_recommendation(has_edge: bool, kelly_pct: float, amount: float) -> str:
    """Generate a recommendation based on the calculation"""
    if not has_edge:
        return "No edge detected. Consider passing on this trade."
    elif kelly_pct > 0.25:
        return f"Strong edge. Recommended bet: ${amount:,.2f}"
    elif kelly_pct > 0.10:
        return f"Moderate edge. Recommended bet: ${amount:,.2f}"
    elif kelly_pct > 0.05:
        return f"Small edge. Consider smaller position: ${amount:,.2f}"
    else:
        return f"Very small edge. Be cautious: ${amount:,.2f}"


def _display_results(console: Console, bankroll: float, probability: float, odds: float, kelly: float, result: dict):
    """Display calculation results"""
    console.print()

    edge = result['edge']
    kelly_data = result['kelly']
    fixed = result['fixed']
    outcomes = result['outcomes']

    # Edge analysis
    edge_color = "green" if edge['has_edge'] else "red"
    console.print("[bold yellow]Edge Analysis[/bold yellow]")
    console.print(f"  Your estimate: [cyan]{probability*100:.0f}%[/cyan]")
    console.print(f"  Market price:  [cyan]{odds*100:.0f}%[/cyan]")
    console.print(f"  Your edge:     [{edge_color}]{edge['edge_pct']:+.1f}%[/{edge_color}]")
    console.print(f"  EV per $1:     [{edge_color}]${edge['ev_per_dollar']:+.3f}[/{edge_color}]")
    console.print()

    if not edge['has_edge']:
        console.print(Panel(
            "[red bold]No Edge Detected[/red bold]\n\n"
            "Your probability estimate is lower than the market price.\n"
            "This means you don't have an edge on this trade.\n\n"
            "[dim]Consider:[/dim]\n"
            "  - Passing on this trade\n"
            "  - Re-evaluating your probability estimate\n"
            "  - Looking for better opportunities",
            border_style="red",
        ))
        return

    # Kelly calculations
    console.print("[bold yellow]Kelly Criterion[/bold yellow]")
    console.print(f"  Full Kelly:       {kelly_data['full_kelly_pct']:.1f}% (${kelly_data['full_kelly_amount']:,.2f})")
    console.print(f"  {kelly*100:.0f}% Kelly:        {kelly_data['fractional_kelly_pct']:.1f}% ([bold green]${kelly_data['fractional_kelly_amount']:,.2f}[/bold green])")
    console.print()

    # Fixed percentages for comparison
    console.print("[bold yellow]Fixed Percentage Alternatives[/bold yellow]")
    fixed_table = Table(show_header=True, box=None)
    fixed_table.add_column("Strategy", style="cyan")
    fixed_table.add_column("Amount", justify="right")

    fixed_table.add_row("1% of bankroll", f"${fixed['one_percent']:,.2f}")
    fixed_table.add_row("2% of bankroll", f"${fixed['two_percent']:,.2f}")
    fixed_table.add_row("5% of bankroll", f"${fixed['five_percent']:,.2f}")

    console.print(fixed_table)
    console.print()

    # Outcomes
    console.print("[bold yellow]If You Bet ${:,.2f}[/bold yellow]".format(kelly_data['fractional_kelly_amount']))
    outcomes_table = Table(show_header=True, box=None)
    outcomes_table.add_column("Outcome", style="cyan")
    outcomes_table.add_column("Result", justify="right")

    outcomes_table.add_row("Shares purchased", f"{outcomes['shares']:,.1f}")
    outcomes_table.add_row("[green]If YES wins[/green]", f"[green]+${outcomes['profit_if_win']:,.2f}[/green] (+{outcomes['roi_if_win']:.0f}%)")
    outcomes_table.add_row("[red]If NO wins[/red]", f"[red]-${outcomes['loss_if_lose']:,.2f}[/red] (-100%)")

    console.print(outcomes_table)
    console.print()

    # Recommendation
    console.print(Panel(
        f"[bold]{result['recommendation']}[/bold]",
        title="[green]Recommendation[/green]",
        border_style="green",
    ))
    console.print()

    # Tips
    console.print("[dim]Tips:[/dim]")
    console.print("[dim]  - Kelly assumes you know the true probability (you don't)[/dim]")
    console.print("[dim]  - Use fractional Kelly (25-50%) to reduce variance[/dim]")
    console.print("[dim]  - Never bet more than you can afford to lose[/dim]")
    console.print("[dim]  - Diversify across multiple uncorrelated bets[/dim]")
