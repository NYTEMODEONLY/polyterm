"""Watch command - monitor specific markets with alerts"""

import click
from rich.console import Console

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...core.scanner import MarketScanner
from ...core.alerts import AlertManager


@click.command()
@click.option("--market", required=True, help="Market ID or search term")
@click.option("--threshold", default=10.0, help="Probability change threshold (%)")
@click.option("--volume-threshold", default=50.0, help="Volume change threshold (%)")
@click.option("--interval", default=60, help="Check interval in seconds")
@click.option("--notify", is_flag=True, help="Enable system notifications")
@click.pass_context
def watch(ctx, market, threshold, volume_threshold, interval, notify):
    """Watch specific markets with customizable alerts"""
    
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
    
    # Find market
    console.print(f"[cyan]Searching for market: {market}[/cyan]")
    
    try:
        # Try as ID first
        market_data = gamma_client.get_market(market)
        market_id = market_data.get("id")
        market_title = market_data.get("question")
    except Exception:
        # Search by term
        results = gamma_client.search_markets(market, limit=5)
        if not results:
            console.print(f"[red]No markets found for: {market}[/red]")
            return
        
        # Show options
        console.print("\n[yellow]Multiple markets found:[/yellow]")
        for i, m in enumerate(results):
            console.print(f"  {i+1}. {m.get('question')}")
        
        choice = click.prompt("Select market number", type=int, default=1)
        selected = results[choice - 1]
        market_id = selected.get("id")
        market_title = selected.get("question")
    
    console.print(f"\n[green]Watching:[/green] {market_title}")
    console.print(f"[cyan]Probability threshold:[/cyan] {threshold}%")
    console.print(f"[cyan]Volume threshold:[/cyan] {volume_threshold}%")
    console.print(f"[cyan]Check interval:[/cyan] {interval}s\n")
    
    # Initialize scanner and alerts
    scanner = MarketScanner(
        gamma_client,
        clob_client,
        subgraph_client,
        check_interval=interval,
    )
    
    alert_manager = AlertManager(enable_system_notifications=notify)
    
    # Add alert callback
    def on_shift(shift_data):
        thresholds = {
            "probability": threshold,
            "volume": volume_threshold,
        }
        alert_manager.process_shift(shift_data, thresholds)
    
    scanner.add_shift_callback(on_shift)
    
    # Start monitoring
    try:
        scanner.start_monitoring(
            market_ids=[market_id],
            thresholds={
                "probability": threshold,
                "volume": volume_threshold,
            },
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped watching market[/yellow]")
    finally:
        gamma_client.close()
        clob_client.close()

