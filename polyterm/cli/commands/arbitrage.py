"""Arbitrage command - scan for arbitrage opportunities"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...db.database import Database
from ...core.arbitrage import ArbitrageScanner, KalshiArbitrageScanner
from ...utils.json_output import print_json


@click.command()
@click.option("--min-spread", default=0.025, help="Minimum spread for arbitrage (default: 2.5%)")
@click.option("--limit", default=10, help="Maximum opportunities to show")
@click.option("--include-kalshi", is_flag=True, help="Include Kalshi cross-platform arbitrage")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def arbitrage(ctx, min_spread, limit, include_kalshi, output_format):
    """Scan for arbitrage opportunities across markets"""

    config = ctx.obj["config"]
    console = Console()

    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
    )
    db = Database()

    try:
        # Initialize scanner
        scanner = ArbitrageScanner(
            database=db,
            gamma_client=gamma_client,
            clob_client=clob_client,
            min_spread=min_spread,
        )

        if output_format != 'json':
            console.print(f"[cyan]Scanning for arbitrage opportunities (min spread: {min_spread:.1%})...[/cyan]\n")

        # Get markets
        markets = gamma_client.get_markets(limit=100, active=True, closed=False)

        # Scan for opportunities
        all_opportunities = []

        # Intra-market arbitrage
        intra_opps = scanner.scan_intra_market_arbitrage(markets)
        all_opportunities.extend(intra_opps)

        # Correlated market arbitrage
        correlated_opps = scanner.scan_correlated_markets(markets)
        all_opportunities.extend(correlated_opps)

        # Kalshi cross-platform (if enabled and configured)
        if include_kalshi and config.kalshi_api_key:
            kalshi_scanner = KalshiArbitrageScanner(
                database=db,
                gamma_client=gamma_client,
                kalshi_api_key=config.kalshi_api_key,
            )
            kalshi_opps = kalshi_scanner.scan_cross_platform_arbitrage(min_spread)
            all_opportunities.extend(kalshi_opps)

        # Sort by profit
        all_opportunities.sort(key=lambda x: x.net_profit, reverse=True)
        all_opportunities = all_opportunities[:limit]

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'min_spread': min_spread,
                'count': len(all_opportunities),
                'opportunities': [
                    {
                        'type': opp.type,
                        'market1_id': opp.market1_id,
                        'market2_id': opp.market2_id,
                        'market1_title': opp.market1_title,
                        'market2_title': opp.market2_title,
                        'spread': opp.spread,
                        'spread_pct': opp.spread * 100,
                        'expected_profit_usd': opp.net_profit,
                        'confidence': opp.confidence,
                    }
                    for opp in all_opportunities
                ],
            }
            print_json(output)
            return

        if not all_opportunities:
            console.print("[yellow]No arbitrage opportunities found above minimum spread[/yellow]")
            return

        # Create table
        table = Table(title=f"Arbitrage Opportunities (Spread >= {min_spread:.1%})")

        table.add_column("Type", style="cyan")
        table.add_column("Market(s)", style="green", max_width=40)
        table.add_column("Spread", justify="right", style="yellow")
        table.add_column("Profit ($100)", justify="right", style="bold green")
        table.add_column("Confidence", justify="center")

        for opp in all_opportunities:
            type_display = opp.type.replace('_', ' ').title()

            if opp.type == 'intra_market':
                market_display = opp.market1_title[:40]
            else:
                market_display = f"{opp.market1_title[:18]}... vs {opp.market2_title[:18]}..."

            confidence_style = "green" if opp.confidence == 'high' else "yellow" if opp.confidence == 'medium' else "dim"

            table.add_row(
                type_display,
                market_display,
                f"{opp.spread:.1%}",
                f"${opp.net_profit:.2f}",
                f"[{confidence_style}]{opp.confidence}[/{confidence_style}]",
            )

        console.print(table)

        # Summary
        total_potential = sum(opp.net_profit for opp in all_opportunities)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Opportunities found: {len(all_opportunities)}")
        console.print(f"  Total potential profit (per $100): ${total_potential:.2f}")

        if not include_kalshi:
            console.print(f"\n[dim]Tip: Use --include-kalshi to scan cross-platform opportunities[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()
