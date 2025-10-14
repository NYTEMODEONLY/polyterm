"""Whales command - track large trades"""

import click
from rich.console import Console
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...core.analytics import AnalyticsEngine
from ...utils.formatting import format_timestamp, format_volume


@click.command()
@click.option("--min-amount", default=10000, help="Minimum trade size to track")
@click.option("--market", default=None, help="Filter by market ID")
@click.option("--hours", default=24, help="Hours of history to check")
@click.option("--limit", default=20, help="Maximum number of trades to show")
@click.pass_context
def whales(ctx, min_amount, market, hours, limit):
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
    
    console.print(f"[cyan]Tracking whale trades ≥ ${min_amount:,.0f}[/cyan]")
    console.print(f"[cyan]Lookback period: {hours} hours[/cyan]\n")
    
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
        
        if not whale_trades:
            console.print("[yellow]No whale trades found[/yellow]")
            return
        
        # Create table
        table = Table(title=f"Whale Trades (Last {hours}h)")
        
        table.add_column("Time", style="cyan")
        table.add_column("Trader", style="yellow")
        table.add_column("Market", style="green", no_wrap=False, max_width=40)
        table.add_column("Side", justify="center")
        table.add_column("Size", justify="right", style="magenta")
        table.add_column("Price", justify="right")
        table.add_column("Notional", justify="right", style="bold")
        
        for trade in whale_trades:
            # Get market info
            try:
                market_data = gamma_client.get_market(trade.market_id)
                market_name = market_data.get("question", "Unknown")[:40]
            except:
                market_name = trade.market_id[:20]
            
            # Format side
            side_style = "green" if trade.outcome == "YES" else "red"
            side_text = f"[{side_style}]{trade.outcome}[/{side_style}]"
            
            table.add_row(
                format_timestamp(trade.timestamp),
                f"{trade.trader[:8]}...",
                market_name,
                side_text,
                format_volume(trade.shares, use_short=False),
                f"${trade.price:.4f}",
                f"${trade.notional:,.0f}",
            )
        
        console.print(table)
        
        # Summary
        total_volume = sum(t.notional for t in whale_trades)
        unique_traders = len(set(t.trader for t in whale_trades))
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Total trades: {len(whale_trades)}")
        console.print(f"  Total volume: ${total_volume:,.0f}")
        console.print(f"  Unique traders: {unique_traders}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()

