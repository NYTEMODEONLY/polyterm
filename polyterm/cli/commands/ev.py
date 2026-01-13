"""Expected Value Calculator - Calculate EV and optimal bet sizing"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", default=None, help="Market to analyze")
@click.option("--probability", "-p", type=float, default=None, help="Your probability estimate (0-1)")
@click.option("--stake", "-s", type=float, default=100, help="Stake amount ($)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def ev(ctx, market, probability, stake, interactive, output_format):
    """Calculate expected value and optimal position size

    The foundation of profitable trading. Enter your probability
    estimate to see if a bet has positive expected value.

    EV Formula: (Prob * Payout) - (1-Prob * Stake)
    Kelly: (bp - q) / b where b=odds, p=win prob, q=lose prob

    Examples:
        polyterm ev -m "bitcoin" -p 0.65        # Your 65% estimate
        polyterm ev -m "election" -p 0.55 -s 500  # $500 stake
        polyterm ev -i                          # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        console.print()
        console.print(Panel("[bold]Expected Value Calculator[/bold]", border_style="cyan"))
        console.print()
        console.print("[bold]Calculate if a trade has positive expected value[/bold]")
        console.print()

        market = Prompt.ask("[cyan]Market name[/cyan]")

        prob_str = Prompt.ask("[cyan]Your probability estimate (e.g., 0.65 or 65%)[/cyan]")
        try:
            if '%' in prob_str:
                probability = float(prob_str.replace('%', '')) / 100
            else:
                probability = float(prob_str)
        except ValueError:
            console.print("[red]Invalid probability[/red]")
            return

        stake_str = Prompt.ask("[cyan]Stake amount ($)[/cyan]", default="100")
        try:
            stake = float(stake_str)
        except ValueError:
            stake = 100

        console.print()

    if not market:
        console.print("[yellow]Please specify a market with -m or use --interactive[/yellow]")
        return

    if probability is None:
        console.print("[yellow]Please specify your probability estimate with -p[/yellow]")
        return

    if probability < 0 or probability > 1:
        console.print("[red]Probability must be between 0 and 1[/red]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Find market
        markets = gamma_client.search_markets(market, limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': f'Market not found: {market}'})
            else:
                console.print(f"[yellow]No markets found for '{market}'[/yellow]")
            return

        m = markets[0]
        title = m.get('question', m.get('title', ''))[:60]

        # Get current price
        market_price = 0.5
        tokens = m.get('tokens', [])
        for token in tokens:
            if token.get('outcome', '').upper() == 'YES':
                try:
                    market_price = float(token.get('price', 0.5))
                except (ValueError, TypeError):
                    pass
                break

        # Calculate EV for YES side
        yes_analysis = _calculate_ev(probability, market_price, stake, 'YES')

        # Calculate EV for NO side (using inverse probability)
        no_prob = 1 - probability
        no_price = 1 - market_price
        no_analysis = _calculate_ev(no_prob, no_price, stake, 'NO')

        if output_format == 'json':
            print_json({
                'success': True,
                'market': title,
                'market_price': market_price,
                'your_probability': probability,
                'stake': stake,
                'yes_analysis': yes_analysis,
                'no_analysis': no_analysis,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]EV Analysis: {title}[/bold]", border_style="cyan"))
        console.print()

        # Market vs Your view
        console.print("[bold]Market vs Your View:[/bold]")
        console.print()

        view_table = Table(show_header=True, header_style="bold cyan", box=None)
        view_table.add_column("", width=20)
        view_table.add_column("Market", width=12, justify="center")
        view_table.add_column("You", width=12, justify="center")
        view_table.add_column("Edge", width=12, justify="center")

        edge = probability - market_price
        edge_color = "green" if edge > 0 else "red" if edge < 0 else "white"

        view_table.add_row(
            "YES Probability",
            f"{market_price:.1%}",
            f"{probability:.1%}",
            f"[{edge_color}]{edge:+.1%}[/{edge_color}]",
        )
        view_table.add_row(
            "NO Probability",
            f"{1 - market_price:.1%}",
            f"{1 - probability:.1%}",
            f"[{'red' if edge > 0 else 'green'}]{-edge:+.1%}[/]",
        )

        console.print(view_table)
        console.print()

        # EV Analysis
        console.print(f"[bold]Expected Value Analysis (${stake:,.0f} stake):[/bold]")
        console.print()

        ev_table = Table(show_header=True, header_style="bold cyan", box=None)
        ev_table.add_column("Side", width=8)
        ev_table.add_column("Price", width=10, justify="center")
        ev_table.add_column("Win Payout", width=12, justify="right")
        ev_table.add_column("Expected Value", width=15, justify="right")
        ev_table.add_column("ROI", width=10, justify="center")
        ev_table.add_column("Verdict", width=15, justify="center")

        for analysis in [yes_analysis, no_analysis]:
            ev_color = "green" if analysis['ev'] > 0 else "red"
            verdict = "[green]BET[/green]" if analysis['ev'] > 0 else "[red]PASS[/red]"

            ev_table.add_row(
                f"[{'green' if analysis['side'] == 'YES' else 'red'}]{analysis['side']}[/]",
                f"{analysis['price']:.2%}",
                f"${analysis['win_payout']:,.2f}",
                f"[{ev_color}]${analysis['ev']:+,.2f}[/{ev_color}]",
                f"[{ev_color}]{analysis['roi']:+.1%}[/{ev_color}]",
                verdict,
            )

        console.print(ev_table)
        console.print()

        # Kelly Criterion
        console.print("[bold]Kelly Criterion (Optimal Sizing):[/bold]")
        console.print()

        kelly_table = Table(show_header=True, header_style="bold cyan", box=None)
        kelly_table.add_column("Side", width=8)
        kelly_table.add_column("Full Kelly", width=15, justify="center")
        kelly_table.add_column("Half Kelly", width=15, justify="center")
        kelly_table.add_column("Quarter Kelly", width=15, justify="center")

        # Only show Kelly for positive EV bets
        for analysis in [yes_analysis, no_analysis]:
            if analysis['kelly_fraction'] > 0:
                kelly_table.add_row(
                    analysis['side'],
                    f"{analysis['kelly_fraction']:.1%} (${analysis['kelly_stake']:,.0f})",
                    f"{analysis['kelly_fraction']/2:.1%} (${analysis['kelly_stake']/2:,.0f})",
                    f"{analysis['kelly_fraction']/4:.1%} (${analysis['kelly_stake']/4:,.0f})",
                )
            else:
                kelly_table.add_row(
                    analysis['side'],
                    "[dim]No bet[/dim]",
                    "[dim]No bet[/dim]",
                    "[dim]No bet[/dim]",
                )

        console.print(kelly_table)
        console.print()

        # Recommendation
        console.print("[bold]Recommendation:[/bold]")
        console.print()

        best = yes_analysis if yes_analysis['ev'] > no_analysis['ev'] else no_analysis

        if best['ev'] > 0:
            console.print(f"  [green]BET {best['side']}[/green] - Positive EV of ${best['ev']:+.2f}")
            console.print(f"  Your edge: {abs(edge):.1%}")
            console.print()

            # Risk considerations
            if best['kelly_fraction'] > 0.25:
                console.print("  [yellow]Warning: High Kelly suggests large edge.[/yellow]")
                console.print("  [yellow]Consider if your probability estimate is accurate.[/yellow]")

            if stake > best['kelly_stake']:
                console.print(f"  [yellow]Your stake (${stake:,.0f}) exceeds full Kelly (${best['kelly_stake']:,.0f})[/yellow]")
                console.print("  [yellow]Consider reducing position size.[/yellow]")

        else:
            console.print("  [red]NO BET[/red] - Neither side has positive expected value")
            console.print("  The market price appears fair given your probability estimate.")

        console.print()

        # Breakeven analysis
        console.print("[bold]Breakeven Analysis:[/bold]")
        console.print()
        console.print(f"  YES breakeven probability: {market_price:.1%}")
        console.print(f"  NO breakeven probability: {1 - market_price:.1%}")
        console.print()
        console.print("[dim]Your estimate must exceed breakeven for positive EV.[/dim]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _calculate_ev(prob: float, price: float, stake: float, side: str) -> dict:
    """Calculate expected value and Kelly criterion"""
    # Shares purchased (simplified)
    shares = stake / price if price > 0 else 0

    # Win payout ($1 per share)
    win_payout = shares

    # Expected value
    # EV = (prob * win_amount) - ((1-prob) * lose_amount)
    ev = (prob * (win_payout - stake)) - ((1 - prob) * stake)

    # ROI
    roi = ev / stake if stake > 0 else 0

    # Kelly Criterion
    # f* = (bp - q) / b
    # where b = decimal odds - 1, p = win prob, q = lose prob
    if price > 0 and price < 1:
        decimal_odds = 1 / price
        b = decimal_odds - 1
        q = 1 - prob

        kelly = (b * prob - q) / b if b > 0 else 0
        kelly = max(0, kelly)  # Can't bet negative
    else:
        kelly = 0

    # Assume $10,000 bankroll for Kelly stake calculation
    bankroll = 10000
    kelly_stake = kelly * bankroll

    return {
        'side': side,
        'price': price,
        'shares': shares,
        'win_payout': win_payout,
        'ev': ev,
        'roi': roi,
        'kelly_fraction': kelly,
        'kelly_stake': kelly_stake,
    }
