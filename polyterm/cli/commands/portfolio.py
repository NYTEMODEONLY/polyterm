"""Portfolio command - view user positions"""

import click
from rich.console import Console
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...core.analytics import AnalyticsEngine


@click.command()
@click.option("--wallet", default=None, help="Wallet address (or use config)")
@click.pass_context
def portfolio(ctx, wallet):
    """View portfolio and positions"""
    
    config = ctx.obj["config"]
    console = Console()
    
    # Get wallet address
    if not wallet:
        wallet = config.wallet_address
    
    if not wallet:
        console.print("[red]Error: No wallet address provided[/red]")
        console.print("[yellow]Use --wallet flag or set in config[/yellow]")
        return
    
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
    
    console.print(f"[cyan]Loading portfolio for:[/cyan] {wallet}\n")
    
    try:
        # Get portfolio analytics
        portfolio_data = analytics.get_portfolio_analytics(wallet)
        
        # Check for error from graceful degradation
        if portfolio_data.get("error"):
            console.print(f"[yellow]{portfolio_data['error']}[/yellow]")
            if portfolio_data.get("note"):
                console.print(f"[dim]{portfolio_data['note']}[/dim]")
            return
        
        if not portfolio_data.get("positions"):
            console.print("[yellow]No positions found[/yellow]")
            return
        
        # Display summary
        console.print("[bold]Portfolio Summary:[/bold]")
        console.print(f"  Total Positions: {portfolio_data['total_positions']}")
        console.print(f"  Total Value: ${portfolio_data['total_value']:,.2f}")
        console.print(f"  Total P&L: ${portfolio_data['total_pnl']:,.2f}")
        console.print(f"  ROI: {portfolio_data['roi_percent']:,.1f}%\n")
        
        # Display positions
        table = Table(title="Positions")
        
        table.add_column("Market", style="cyan", no_wrap=False, max_width=50)
        table.add_column("Outcome", justify="center")
        table.add_column("Shares", justify="right", style="yellow")
        table.add_column("Avg Price", justify="right")
        table.add_column("Value", justify="right", style="green")
        table.add_column("P&L", justify="right")
        
        for position in portfolio_data["positions"]:
            market_id = position.get("market")
            outcome = position.get("outcome", "")
            shares = float(position.get("shares", 0))
            avg_price = float(position.get("averagePrice", 0))
            realized_pnl = float(position.get("realizedPnL", 0))
            unrealized_pnl = float(position.get("unrealizedPnL", 0))
            
            # Get market name
            try:
                market_data = gamma_client.get_market(market_id)
                market_name = market_data.get("question", "Unknown")[:50]
            except Exception:
                market_name = market_id[:30]
            
            value = shares * avg_price
            total_pnl = realized_pnl + unrealized_pnl
            
            # Format outcome
            outcome_style = "green" if outcome == "YES" else "red"
            outcome_text = f"[{outcome_style}]{outcome}[/{outcome_style}]"
            
            # Format P&L
            pnl_style = "green" if total_pnl >= 0 else "red"
            pnl_text = f"[{pnl_style}]${total_pnl:,.2f}[/{pnl_style}]"
            
            table.add_row(
                market_name,
                outcome_text,
                f"{shares:.2f}",
                f"${avg_price:.4f}",
                f"${value:,.2f}",
                pnl_text,
            )
        
        console.print(table)
    
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback
        console.print(f"[red]{traceback.format_exc()}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()

