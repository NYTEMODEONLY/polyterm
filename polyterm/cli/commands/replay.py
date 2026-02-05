"""Replay command - historical playback"""

import click
import time
from rich.console import Console
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...utils.formatting import format_timestamp, format_probability


@click.command()
@click.option("--market", required=True, help="Market ID or search term")
@click.option("--hours", default=24, help="Hours of history to show")
@click.option("--speed", default=1.0, help="Playback speed multiplier")
@click.option("--trades", is_flag=True, help="Show individual trades")
@click.pass_context
def replay(ctx, market, hours, speed, trades):
    """Replay historical market data"""
    
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
    
    console.print(f"[cyan]Loading market: {market}[/cyan]")
    
    try:
        # Find market
        try:
            market_data = gamma_client.get_market(market)
            market_id = market_data.get("id")
            market_title = market_data.get("question")
        except Exception:
            results = gamma_client.search_markets(market, limit=1)
            if not results:
                console.print(f"[red]Market not found: {market}[/red]")
                return
            market_id = results[0].get("id")
            market_title = results[0].get("question")
        
        console.print(f"[green]Replaying:[/green] {market_title}\n")
        
        # Get historical trades from Gamma API
        import time as time_module
        end_time = int(time_module.time())
        start_time = end_time - (hours * 3600)
        
        # Use Gamma API instead of Subgraph
        historical_trades = gamma_client.get_market_trades(
            market_id,
            limit=1000,
        )
        
        # Filter by time window
        historical_trades = [
            t for t in historical_trades
            if start_time <= int(t.get("timestamp", 0)) <= end_time
        ]
        
        # Sort by timestamp ascending for replay
        historical_trades = sorted(historical_trades, key=lambda t: int(t.get("timestamp", 0)))
        
        if not historical_trades:
            console.print("[yellow]No historical data found for this time period[/yellow]")
            return
        
        console.print(f"[cyan]Found {len(historical_trades)} trades in last {hours} hours[/cyan]\n")
        
        if trades:
            # Replay individual trades
            table = Table(title="Historical Trades")
            table.add_column("Time", style="cyan")
            table.add_column("Side", justify="center")
            table.add_column("Price", justify="right", style="yellow")
            table.add_column("Shares", justify="right")
            table.add_column("Trader", style="dim")
            
            for trade in historical_trades:
                timestamp = int(trade.get("timestamp", 0))
                price = float(trade.get("price", 0))
                shares = float(trade.get("shares", 0))
                outcome = trade.get("outcome", "")
                trader = trade.get("trader", "")
                
                side_style = "green" if outcome == "YES" else "red"
                
                table.add_row(
                    format_timestamp(timestamp),
                    f"[{side_style}]{outcome}[/{side_style}]",
                    f"{price:.4f}",
                    f"{shares:.2f}",
                    f"{trader[:8]}...",
                )
            
            console.print(table)
        else:
            # Show price movement summary
            prices = [(int(t.get("timestamp", 0)), float(t.get("price", 0))) for t in historical_trades]
            
            # Group by time intervals
            interval_seconds = 3600  # 1 hour intervals
            intervals = {}
            
            for timestamp, price in prices:
                interval = (timestamp // interval_seconds) * interval_seconds
                if interval not in intervals:
                    intervals[interval] = []
                intervals[interval].append(price)
            
            # Calculate average price per interval
            table = Table(title="Price Movement (Hourly Averages)")
            table.add_column("Time", style="cyan")
            table.add_column("Avg Price", justify="right", style="yellow")
            table.add_column("Probability", justify="right", style="green")
            table.add_column("Change", justify="right")
            
            sorted_intervals = sorted(intervals.items())
            prev_price = None
            
            for interval_time, interval_prices in sorted_intervals:
                avg_price = sum(interval_prices) / len(interval_prices)
                probability = avg_price * 100
                
                if prev_price:
                    change = ((avg_price - prev_price) / prev_price * 100)
                    change_style = "green" if change > 0 else "red" if change < 0 else "white"
                    change_text = f"[{change_style}]{change:+.1f}%[/{change_style}]"
                else:
                    change_text = "—"
                
                table.add_row(
                    format_timestamp(interval_time),
                    f"${avg_price:.4f}",
                    format_probability(probability),
                    change_text,
                )
                
                prev_price = avg_price
            
            console.print(table)
        
        # Summary statistics
        first_price = float(historical_trades[0].get("price", 0))
        last_price = float(historical_trades[-1].get("price", 0))
        total_change = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
        
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Start price: ${first_price:.4f} ({first_price * 100:.1f}%)")
        console.print(f"  End price: ${last_price:.4f} ({last_price * 100:.1f}%)")
        console.print(f"  Total change: {total_change:+.1f}%")
        console.print(f"  Total trades: {len(historical_trades)}")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()

