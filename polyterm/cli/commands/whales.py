"""Whales command - track large trades"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...core.analytics import AnalyticsEngine
from ...utils.formatting import format_timestamp, format_volume
from ...utils.json_output import print_json


@click.command()
@click.option("--min-amount", default=10000, help="Minimum trade size to track")
@click.option("--market", default=None, help="Filter by market ID")
@click.option("--hours", default=24, help="Hours of history to check")
@click.option("--limit", default=20, help="Maximum number of trades to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def whales(ctx, min_amount, market, hours, limit, output_format):
    """Track large trades (whale activity)"""

    config = ctx.obj["config"]
    console = Console()
    
    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )
    subgraph_client = SubgraphClient(endpoint=config.subgraph_endpoint)
    
    # Initialize analytics
    analytics = AnalyticsEngine(gamma_client, clob_client, subgraph_client)
    
    console.print(f"[cyan]Tracking high-volume markets ≥ ${min_amount:,.0f}[/cyan]")
    console.print(f"[cyan]Period: Last {hours} hours[/cyan]")
    console.print(f"[dim]Note: Showing markets with significant 24hr volume (individual trades not available from API)[/dim]\n")
    
    try:
        # Get whale trades
        whale_trades = analytics.track_whale_trades(
            min_notional=min_amount,
            lookback_hours=hours,
        )

        # Filter by market if specified
        if market:
            whale_trades = [w for w in whale_trades if w.market_id == market]

        # Limit results
        whale_trades = whale_trades[:limit]

        # JSON output mode
        if output_format == 'json':
            total_volume = sum(t.notional for t in whale_trades)
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'min_amount': min_amount,
                'hours': hours,
                'count': len(whale_trades),
                'total_volume': total_volume,
                'trades': [
                    {
                        'market_id': t.market_id,
                        'market_title': t.data.get('_market_title', t.market_id),
                        'outcome': t.outcome,
                        'price': t.price,
                        'notional': t.notional,
                        'timestamp': t.timestamp,
                    }
                    for t in whale_trades
                ],
            }
            print_json(output)
            return

        if not whale_trades:
            console.print("[yellow]No whale trades found[/yellow]")
            return

        # Create table
        table = Table(title=f"High Volume Markets (Last {hours}h)")

        table.add_column("Market", style="green", no_wrap=False, max_width=50)
        table.add_column("Trend", justify="center")
        table.add_column("Last Price", justify="right")
        table.add_column("24h Volume", justify="right", style="bold yellow")

        for trade in whale_trades:
            # Get market name from cached data or fallback
            market_name = trade.data.get('_market_title', trade.market_id)[:50]

            # Format trend/outcome
            trend_style = "green" if trade.outcome == "YES" else "red" if trade.outcome == "NO" else "dim"
            trend_text = f"[{trend_style}]{trade.outcome}[/{trend_style}]"

            table.add_row(
                market_name,
                trend_text,
                f"${trade.price:.3f}" if trade.price > 0 else "[dim]N/A[/dim]",
                f"${trade.notional:,.0f}",
            )

        console.print(table)

        # Summary
        total_volume = sum(t.notional for t in whale_trades)

        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  High-volume markets: {len(whale_trades)}")
        console.print(f"  Total 24hr volume: ${total_volume:,.0f}")
        console.print(f"  Average per market: ${total_volume/len(whale_trades):,.0f}" if whale_trades else "N/A")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()

