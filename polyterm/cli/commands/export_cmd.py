"""Export command - data export to JSON/CSV"""

import click
import json
import csv
import sys
from rich.console import Console

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient


@click.command(name="export")
@click.option("--market", required=True, help="Market ID or search term")
@click.option("--format", "output_format", type=click.Choice(["json", "csv"]), default="json", help="Output format")
@click.option("--hours", default=24, help="Hours of data to export")
@click.option("--output", "-o", default=None, help="Output file (default: stdout)")
@click.pass_context
def export(ctx, market, output_format, hours, output):
    """Export market data to JSON or CSV"""
    
    config = ctx.obj["config"]
    console = Console(stderr=True)  # Use stderr for messages
    
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
    
    try:
        # Find market
        try:
            market_data = gamma_client.get_market(market)
            market_id = market_data.get("id")
        except:
            results = gamma_client.search_markets(market, limit=1)
            if not results:
                console.print(f"[red]Market not found: {market}[/red]")
                return
            market_id = results[0].get("id")
            market_data = results[0]
        
        console.print(f"[cyan]Exporting data for:[/cyan] {market_data.get('question')}")
        console.print(f"[cyan]Format:[/cyan] {output_format}")
        console.print(f"[cyan]Time window:[/cyan] {hours} hours\n")
        
        # Get historical trades
        import time
        end_time = int(time.time())
        start_time = end_time - (hours * 3600)
        
        trades = subgraph_client.get_market_trades(
            market_id,
            first=1000,
            order_by="timestamp",
            order_direction="desc",
        )
        
        # Filter by time
        trades = [
            t for t in trades
            if start_time <= int(t.get("timestamp", 0)) <= end_time
        ]
        
        # Get market statistics
        stats = subgraph_client.get_market_statistics(market_id)
        
        # Prepare export data
        export_data = {
            "market": {
                "id": market_id,
                "question": market_data.get("question"),
                "total_volume": stats.get("totalVolume", 0),
                "total_liquidity": stats.get("totalLiquidity", 0),
                "trade_count": stats.get("tradeCount", 0),
            },
            "trades": trades,
            "export_metadata": {
                "exported_at": int(time.time()),
                "time_window_hours": hours,
                "trade_count": len(trades),
            }
        }
        
        # Export in requested format
        if output_format == "json":
            output_data = json.dumps(export_data, indent=2)
        else:  # CSV
            # Flatten trades for CSV
            csv_data = []
            for trade in trades:
                csv_data.append({
                    "market_id": market_id,
                    "market_question": market_data.get("question"),
                    "timestamp": trade.get("timestamp"),
                    "trader": trade.get("trader"),
                    "outcome": trade.get("outcome"),
                    "shares": trade.get("shares"),
                    "price": trade.get("price"),
                    "transaction_hash": trade.get("transactionHash"),
                })
            
            # Write CSV to string
            if csv_data:
                import io
                output_buffer = io.StringIO()
                writer = csv.DictWriter(output_buffer, fieldnames=csv_data[0].keys())
                writer.writeheader()
                writer.writerows(csv_data)
                output_data = output_buffer.getvalue()
            else:
                output_data = ""
        
        # Output
        if output:
            with open(output, "w") as f:
                f.write(output_data)
            console.print(f"[green]Data exported to:[/green] {output}")
        else:
            # Print to stdout
            print(output_data)
        
        console.print(f"[green]Exported {len(trades)} trades[/green]")
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()

