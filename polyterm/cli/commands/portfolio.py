"""Portfolio command - view user positions"""

import click
from rich.console import Console
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...core.analytics import AnalyticsEngine
from ...utils.json_output import safe_float


def _extract_position_fields(position):
    """Normalize position fields across Data API and legacy Subgraph shapes."""
    market_id = (
        position.get("market")
        or position.get("market_id")
        or position.get("conditionId")
        or ""
    )
    title = position.get("title", "") or position.get("question", "")
    outcome = (position.get("outcome") or position.get("side") or "").upper()

    shares = safe_float(position.get("size", position.get("shares", position.get("quantity", 0))))
    avg_price = safe_float(
        position.get("averagePrice", position.get("avgPrice", position.get("entryPrice", 0)))
    )
    current_value = safe_float(
        position.get("currentValue", position.get("value", position.get("current_value", 0)))
    )
    explicit_pnl = position.get("pnl")
    if explicit_pnl is not None:
        total_pnl = safe_float(explicit_pnl)
    else:
        realized = position.get("realizedPnL", position.get("realizedPnl", 0))
        unrealized = position.get("unrealizedPnL", position.get("unrealizedPnl", 0))
        total_pnl = safe_float(realized) + safe_float(unrealized)

    if avg_price == 0 and shares > 0:
        initial_value = safe_float(position.get("initialValue", position.get("costBasis", 0)))
        if initial_value > 0:
            avg_price = initial_value / shares

    if current_value == 0 and shares > 0 and avg_price > 0:
        current_value = shares * avg_price

    return {
        "market_id": market_id,
        "title": title,
        "outcome": outcome,
        "shares": shares,
        "avg_price": avg_price,
        "current_value": current_value,
        "total_pnl": total_pnl,
    }


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
    # Initialize analytics (Data API-backed; no Subgraph dependency required)
    analytics = AnalyticsEngine(gamma_client, clob_client, None)
    
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
            normalized = _extract_position_fields(position)

            market_id = normalized["market_id"]
            market_name = normalized["title"][:50] if normalized["title"] else ""

            if not market_name and market_id:
                try:
                    market_data = gamma_client.get_market(market_id)
                    market_name = market_data.get("question", "Unknown")[:50]
                except Exception:
                    market_name = market_id[:30]
            elif not market_name:
                market_name = "Unknown"

            outcome = normalized["outcome"]
            shares = normalized["shares"]
            avg_price = normalized["avg_price"]
            value = normalized["current_value"]
            total_pnl = normalized["total_pnl"]

            if outcome == "YES":
                outcome_text = f"[green]{outcome}[/green]"
            elif outcome == "NO":
                outcome_text = f"[red]{outcome}[/red]"
            elif outcome:
                outcome_text = outcome
            else:
                outcome_text = "N/A"

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
