"""Explain move command - recent market price movement attribution."""

import click
from rich.console import Console
from rich.panel import Panel

from ...api.clob import CLOBClient
from ...api.gamma import GammaClient
from ...core.market_move import MarketMoveExplainer
from ...utils.errors import handle_api_error
from ...utils.json_output import print_json


@click.command("explain-move")
@click.option("--market", "-m", required=True, help="Market slug, URL, Gamma ID, condition ID, token ID, or search term")
@click.option("--hours", default=24, show_default=True, type=int, help="Price-history lookback window to explain")
@click.option("--brief", is_flag=True, help="Show a compact one-screen explanation")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def explain_move(ctx, market, hours, brief, output_format):
    """Explain a recent YES price move for one market"""
    config = ctx.obj["config"]
    console = Console()
    gamma = GammaClient(base_url=config.gamma_base_url, api_key=config.gamma_api_key)
    clob = CLOBClient(rest_endpoint=config.clob_rest_endpoint, ws_endpoint=config.clob_endpoint)

    try:
        result = MarketMoveExplainer(gamma_client=gamma, clob_client=clob).explain(market, hours=hours)
        if output_format == "json":
            print_json({"success": True, "explain_move": result})
            return

        market_info = result["market"]
        move = result["move"]
        console.print(
            Panel(
                f"[bold]{market_info.get('title') or market}[/bold]\n"
                f"Direction: [cyan]{move['direction'].upper()}[/cyan]\n"
                f"{result['headline']}",
                title="Market Move",
                border_style="cyan",
            )
        )

        console.print("[bold]Drivers[/bold]")
        for item in result["drivers"][:3 if brief else None]:
            console.print(f"  + {item}")

        if result["caveats"]:
            console.print("\n[bold yellow]Caveats[/bold yellow]")
            for item in result["caveats"][:3 if brief else None]:
                console.print(f"  ! {item}")

        if not brief and result["quality_flags"]:
            console.print(f"\n[dim]Quality flags: {', '.join(result['quality_flags'])}[/dim]")

    except Exception as exc:
        if output_format == "json":
            print_json({"success": False, "error": str(exc)})
        else:
            handle_api_error(console, exc, "market move explanation")
    finally:
        gamma.close()
        clob.close()
