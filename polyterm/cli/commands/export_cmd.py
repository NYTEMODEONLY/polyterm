"""Export command - data export to JSON/CSV"""

import click
import json
import csv
import sys
import time
import io
from rich.console import Console

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient


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

    try:
        # Find market
        try:
            market_data = gamma_client.get_market(market)
            market_id = market_data.get("id")
        except Exception:
            results = gamma_client.search_markets(market, limit=1)
            if not results:
                console.print(f"[red]Market not found: {market}[/red]")
                return
            market_id = results[0].get("id")
            market_data = results[0]

        console.print(f"[cyan]Exporting data for:[/cyan] {market_data.get('question')}")
        console.print(f"[cyan]Format:[/cyan] {output_format}")
        console.print(f"[cyan]Time window:[/cyan] {hours} hours\n")

        # Parse outcome prices
        outcome_prices = market_data.get('outcomePrices', '[]')
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []

        yes_price = float(outcome_prices[0]) if outcome_prices and len(outcome_prices) > 0 else 0
        no_price = float(outcome_prices[1]) if outcome_prices and len(outcome_prices) > 1 else 0

        # Prepare export data using available Gamma API data
        export_data = {
            "market": {
                "id": market_id,
                "question": market_data.get("question"),
                "slug": market_data.get("slug"),
                "description": market_data.get("description", "")[:500],
                "end_date": market_data.get("endDate"),
                "active": market_data.get("active"),
                "closed": market_data.get("closed"),
                "total_volume": float(market_data.get("volume", 0) or 0),
                "volume_24h": float(market_data.get("volume24hr", 0) or 0),
                "volume_1wk": float(market_data.get("volume1wk", 0) or 0),
                "volume_1mo": float(market_data.get("volume1mo", 0) or 0),
                "liquidity": float(market_data.get("liquidity", 0) or 0),
                "yes_price": yes_price,
                "no_price": no_price,
                "probability": yes_price * 100,
                "spread": float(market_data.get("spread", 0) or 0),
                "best_bid": float(market_data.get("bestBid", 0) or 0),
                "best_ask": float(market_data.get("bestAsk", 0) or 0),
                "price_changes": {
                    "1h": float(market_data.get("oneHourPriceChange", 0) or 0),
                    "1d": float(market_data.get("oneDayPriceChange", 0) or 0),
                    "1wk": float(market_data.get("oneWeekPriceChange", 0) or 0),
                    "1mo": float(market_data.get("oneMonthPriceChange", 0) or 0),
                },
            },
            "export_metadata": {
                "exported_at": int(time.time()),
                "exported_at_iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "time_window_hours": hours,
                "note": "Trade history requires API authentication. This export contains market snapshot data.",
            }
        }

        # Export in requested format
        if output_format == "json":
            output_data = json.dumps(export_data, indent=2)
        else:  # CSV
            # Flatten market data for CSV
            market_info = export_data["market"]
            csv_data = [{
                "id": market_info["id"],
                "question": market_info["question"],
                "slug": market_info["slug"],
                "end_date": market_info["end_date"],
                "active": market_info["active"],
                "closed": market_info["closed"],
                "total_volume": market_info["total_volume"],
                "volume_24h": market_info["volume_24h"],
                "liquidity": market_info["liquidity"],
                "yes_price": market_info["yes_price"],
                "no_price": market_info["no_price"],
                "probability": market_info["probability"],
                "spread": market_info["spread"],
                "price_change_1h": market_info["price_changes"]["1h"],
                "price_change_1d": market_info["price_changes"]["1d"],
                "exported_at": export_data["export_metadata"]["exported_at_iso"],
            }]

            output_buffer = io.StringIO()
            writer = csv.DictWriter(output_buffer, fieldnames=csv_data[0].keys())
            writer.writeheader()
            writer.writerows(csv_data)
            output_data = output_buffer.getvalue()

        # Output
        if output:
            with open(output, "w") as f:
                f.write(output_data)
            console.print(f"[green]Data exported to:[/green] {output}")
        else:
            # Print to stdout
            print(output_data)

        console.print(f"[green]Market data exported successfully[/green]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()

