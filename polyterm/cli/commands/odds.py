"""Odds Converter - Convert between probability and betting odds formats"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...utils.json_output import print_json


@click.command()
@click.argument("value", required=False, type=str)
@click.option("--from", "-f", "from_format", type=click.Choice(["prob", "decimal", "american", "fractional"]), default="prob", help="Input format")
@click.option("--market", "-m", default=None, help="Get odds from a market")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def odds(ctx, value, from_format, market, interactive, output_format):
    """Convert between different odds formats

    Supports: probability, decimal, American, fractional odds.
    Helpful for understanding prices and comparing with other platforms.

    Examples:
        polyterm odds 0.65                    # Convert 65% probability
        polyterm odds 2.5 --from decimal      # Convert decimal odds
        polyterm odds +150 --from american    # Convert American odds
        polyterm odds 3/2 --from fractional   # Convert fractional odds
        polyterm odds --market "bitcoin"      # Get odds from market
        polyterm odds -i                      # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        _interactive_mode(console)
        return

    if market:
        _market_odds(console, config, market, output_format)
        return

    if not value:
        # Show help
        console.print()
        console.print(Panel("[bold]Odds Converter[/bold]", border_style="cyan"))
        console.print()
        console.print("Convert odds between formats:")
        console.print()
        console.print("  [cyan]polyterm odds 0.65[/cyan]              # 65% probability")
        console.print("  [cyan]polyterm odds 2.5 -f decimal[/cyan]    # Decimal odds 2.5")
        console.print("  [cyan]polyterm odds +150 -f american[/cyan]  # American odds +150")
        console.print("  [cyan]polyterm odds -i[/cyan]                # Interactive mode")
        console.print()
        return

    # Parse and convert
    try:
        probability = _parse_to_probability(value, from_format)
    except ValueError as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
        return

    # Calculate all formats
    conversions = _calculate_all_formats(probability)

    if output_format == 'json':
        print_json({
            'success': True,
            'input': value,
            'input_format': from_format,
            'conversions': conversions,
        })
        return

    _display_conversions(console, value, from_format, conversions)


def _parse_to_probability(value: str, from_format: str) -> float:
    """Parse input value to probability"""
    value = value.strip()

    if from_format == 'prob':
        # Accept 0.65, 65%, 65
        if value.endswith('%'):
            prob = float(value[:-1]) / 100
        elif float(value) > 1:
            prob = float(value) / 100
        else:
            prob = float(value)

    elif from_format == 'decimal':
        # Decimal odds (e.g., 2.5)
        decimal = float(value)
        if decimal < 1:
            raise ValueError("Decimal odds must be >= 1")
        prob = 1 / decimal

    elif from_format == 'american':
        # American odds (e.g., +150, -200)
        american = int(value.replace('+', ''))
        if american > 0:
            prob = 100 / (american + 100)
        else:
            prob = abs(american) / (abs(american) + 100)

    elif from_format == 'fractional':
        # Fractional odds (e.g., 3/2)
        if '/' in value:
            num, den = value.split('/')
            decimal = float(num) / float(den) + 1
        else:
            decimal = float(value) + 1
        prob = 1 / decimal

    else:
        raise ValueError(f"Unknown format: {from_format}")

    if not 0 < prob < 1:
        raise ValueError("Probability must be between 0 and 1")

    return prob


def _calculate_all_formats(probability: float) -> dict:
    """Calculate all odds formats from probability"""
    # Decimal odds
    decimal = 1 / probability

    # American odds
    if probability >= 0.5:
        american = -100 * probability / (1 - probability)
        american_str = f"{int(american)}"
    else:
        american = 100 * (1 - probability) / probability
        american_str = f"+{int(american)}"

    # Fractional odds (approximate)
    decimal_minus_one = decimal - 1
    # Find closest simple fraction
    fractions = [
        (1, 10), (1, 5), (1, 4), (1, 3), (2, 5), (1, 2), (3, 5), (2, 3),
        (4, 5), (1, 1), (6, 5), (5, 4), (4, 3), (7, 5), (3, 2), (8, 5),
        (5, 3), (2, 1), (5, 2), (3, 1), (4, 1), (5, 1), (10, 1)
    ]

    closest = min(fractions, key=lambda f: abs(f[0]/f[1] - decimal_minus_one))
    fractional_str = f"{closest[0]}/{closest[1]}"

    # Break-even (at what price you need to exit to break even)
    break_even = probability

    # Edge needed (to be profitable at this price)
    # If true prob > implied prob, you have edge

    return {
        'probability': probability,
        'probability_pct': f"{probability:.1%}",
        'decimal': round(decimal, 2),
        'american': american_str,
        'fractional': fractional_str,
        'break_even': break_even,
        'implied_no': 1 - probability,
        'implied_no_pct': f"{1-probability:.1%}",
    }


def _display_conversions(console: Console, input_value: str, input_format: str, conversions: dict):
    """Display odds conversions"""
    console.print()
    console.print(Panel(f"[bold]Odds Converter[/bold]\nInput: {input_value} ({input_format})", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Format", width=15)
    table.add_column("Value", width=12, justify="right")
    table.add_column("Explanation", width=35)

    table.add_row(
        "Probability",
        f"[bold]{conversions['probability_pct']}[/bold]",
        "Chance of YES winning",
    )

    table.add_row(
        "Decimal",
        f"{conversions['decimal']:.2f}",
        f"$1 bet returns ${conversions['decimal']:.2f}",
    )

    table.add_row(
        "American",
        conversions['american'],
        _explain_american(conversions['american']),
    )

    table.add_row(
        "Fractional",
        conversions['fractional'],
        f"Win {conversions['fractional']} for every 1 staked",
    )

    console.print(table)
    console.print()

    # Additional info
    console.print("[bold]Quick Reference:[/bold]")
    console.print()
    console.print(f"  [green]YES[/green] at {conversions['probability_pct']} = {conversions['decimal']:.2f}x return")
    console.print(f"  [red]NO[/red] at {conversions['implied_no_pct']} = {1/(1-conversions['probability']):.2f}x return")
    console.print()

    # Break-even
    console.print(f"[dim]To break even on YES, true probability must be >= {conversions['probability_pct']}[/dim]")
    console.print()


def _explain_american(american: str) -> str:
    """Explain American odds"""
    if american.startswith('+'):
        return f"Bet $100 to win ${american[1:]}"
    else:
        return f"Bet ${american[1:]} to win $100"


def _interactive_mode(console: Console):
    """Interactive odds conversion mode"""
    from rich.prompt import Prompt

    console.print()
    console.print(Panel("[bold]Odds Converter - Interactive Mode[/bold]", border_style="cyan"))
    console.print()
    console.print("Enter odds in any format. Type 'q' to quit.")
    console.print()
    console.print("[dim]Examples: 0.65, 65%, 2.5d, +150, -200, 3/2[/dim]")
    console.print()

    while True:
        value = Prompt.ask("[cyan]Enter odds[/cyan]")

        if value.lower() in ['q', 'quit', 'exit']:
            break

        # Auto-detect format
        try:
            if value.endswith('%'):
                probability = float(value[:-1]) / 100
            elif value.endswith('d'):
                probability = 1 / float(value[:-1])
            elif value.startswith('+') or value.startswith('-'):
                probability = _parse_to_probability(value, 'american')
            elif '/' in value:
                probability = _parse_to_probability(value, 'fractional')
            elif float(value) > 1:
                probability = 1 / float(value)  # Assume decimal
            else:
                probability = float(value)

            conversions = _calculate_all_formats(probability)

            console.print()
            console.print(f"  Probability: [bold]{conversions['probability_pct']}[/bold]")
            console.print(f"  Decimal:     {conversions['decimal']:.2f}")
            console.print(f"  American:    {conversions['american']}")
            console.print(f"  Fractional:  {conversions['fractional']}")
            console.print()

        except (ValueError, ZeroDivisionError) as e:
            console.print(f"[red]Invalid input: {e}[/red]")
            console.print()


def _market_odds(console: Console, config, market_search: str, output_format: str):
    """Get odds from a market"""
    from ...api.gamma import GammaClient
    from rich.progress import Progress, SpinnerColumn, TextColumn

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

    conversions = _calculate_all_formats(price)

    if output_format == 'json':
        print_json({
            'success': True,
            'market': title,
            'conversions': conversions,
        })
        return

    console.print()
    console.print(Panel(f"[bold]Market Odds[/bold]\n{title[:60]}", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("", width=8)
    table.add_column("Prob", width=8, justify="center")
    table.add_column("Decimal", width=8, justify="center")
    table.add_column("American", width=10, justify="center")

    # YES side
    table.add_row(
        "[green]YES[/green]",
        conversions['probability_pct'],
        f"{conversions['decimal']:.2f}",
        conversions['american'],
    )

    # NO side
    no_conv = _calculate_all_formats(1 - price)
    table.add_row(
        "[red]NO[/red]",
        no_conv['probability_pct'],
        f"{no_conv['decimal']:.2f}",
        no_conv['american'],
    )

    console.print(table)
    console.print()


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
