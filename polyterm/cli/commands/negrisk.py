"""NegRisk Multi-Outcome Arbitrage Scanner"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...core.negrisk import NegRiskAnalyzer
from ...utils.json_output import print_json


@click.command()
@click.option("--min-spread", default=0.02, help="Minimum spread threshold (default: 0.02)")
@click.option("--limit", default=20, help="Maximum opportunities to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def negrisk(ctx, min_spread, limit, output_format):
    """Scan multi-outcome markets for NegRisk arbitrage

    Finds markets where the sum of all YES outcome prices doesn't equal $1.00.
    If total < $1.00, buying all outcomes guarantees profit on resolution.

    Examples:
        polyterm negrisk
        polyterm negrisk --min-spread 0.03
        polyterm negrisk --format json
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(rest_endpoint=config.clob_rest_endpoint)

    try:
        if output_format != 'json':
            console.print()
            console.print(Panel(
                "[bold cyan]NegRisk Multi-Outcome Arbitrage[/bold cyan]\n\n"
                "Scanning multi-outcome markets where sum of YES prices != $1.00.\n"
                "[dim]Buy all outcomes below $1.00 for guaranteed profit.[/dim]",
                border_style="cyan"
            ))
            console.print()
            console.print("[dim]Scanning markets...[/dim]")

        analyzer = NegRiskAnalyzer(gamma_client, clob_client, polymarket_fee=config.get("arbitrage.polymarket_fee", 0.02))
        opportunities = analyzer.scan_all(min_spread=min_spread)

        if output_format == 'json':
            print_json({
                'success': True,
                'min_spread': min_spread,
                'opportunities': opportunities[:limit],
                'total_found': len(opportunities),
            })
            return

        if not opportunities:
            console.print("[yellow]No NegRisk arbitrage opportunities found[/yellow]")
            console.print(f"[dim]Min spread: {min_spread:.1%}[/dim]")
            return

        console.print(f"[green]Found {len(opportunities)} opportunities[/green]")
        console.print()

        for i, opp in enumerate(opportunities[:limit], 1):
            type_color = "green" if opp['type'] == 'underpriced' else "red"
            profit_color = "green" if opp['fee_adjusted_profit'] > 0 else "red"

            console.print(f"[bold]{i}. {opp['event_title'][:60]}[/bold]")
            console.print(f"   Outcomes: {opp['num_outcomes']} | "
                         f"Sum: [{type_color}]${opp['total_yes_price']:.4f}[/{type_color}] | "
                         f"Spread: {opp['spread']:.2%} | "
                         f"Profit/\\$100: [{profit_color}]${opp['profit_per_100']:+.2f}[/{profit_color}]")

            # Show outcomes table for top opportunities
            if i <= 3:
                table = Table(show_header=True, header_style="dim", box=None, padding=(0, 2))
                table.add_column("Outcome", max_width=40)
                table.add_column("YES Price", justify="right", width=10)

                for outcome in opp['outcomes']:
                    table.add_row(
                        outcome['question'][:40],
                        f"${outcome['yes_price']:.4f}",
                    )
                console.print(table)
            console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()
