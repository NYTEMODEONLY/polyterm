"""Thesis command - explainable market-level trade thesis"""

import click
from rich.console import Console
from rich.panel import Panel

from ...api.clob import CLOBClient
from ...api.gamma import GammaClient
from ...core.trade_thesis import TradeThesisEngine
from ...db.database import Database
from ...utils.errors import handle_api_error
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", required=True, help="Market slug, URL, Gamma ID, condition ID, or search term")
@click.option("--brief", is_flag=True, help="Show a compact one-screen thesis")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def thesis(ctx, market, brief, output_format):
    """Generate an explainable trade thesis for one market"""
    config = ctx.obj["config"]
    console = Console()
    gamma = GammaClient(base_url=config.gamma_base_url, api_key=config.gamma_api_key)
    clob = CLOBClient(rest_endpoint=config.clob_rest_endpoint, ws_endpoint=config.clob_endpoint)

    try:
        engine = TradeThesisEngine(gamma_client=gamma, clob_client=clob, database=Database())
        result = engine.build(market)

        if output_format == "json":
            print_json({"success": True, "thesis": result})
            return

        market_info = result["market"]
        thesis_info = result["thesis"]
        console.print(Panel(
            f"[bold]{market_info.get('title') or market}[/bold]\n"
            f"Direction: [cyan]{thesis_info['direction'].upper()}[/cyan]\n"
            f"Confidence: [cyan]{thesis_info['confidence']:.0%}[/cyan]\n"
            f"{thesis_info['summary']}",
            title="Trade Thesis",
            border_style="cyan",
        ))

        console.print("[bold]Evidence[/bold]")
        for item in thesis_info["evidence"][:4 if brief else None]:
            console.print(f"  + {item}")

        if thesis_info["risks"]:
            console.print("\n[bold red]Risks[/bold red]")
            for item in thesis_info["risks"][:4 if brief else None]:
                console.print(f"  ! {item}")

        if not brief:
            console.print("\n[bold]Next Actions[/bold]")
            for item in thesis_info["next_actions"]:
                console.print(f"  - {item}")
            if result["quality_flags"]:
                console.print(f"\n[dim]Quality flags: {', '.join(result['quality_flags'])}[/dim]")

    except Exception as exc:
        if output_format == "json":
            print_json({"success": False, "error": str(exc)})
        else:
            handle_api_error(console, exc, "trade thesis")
    finally:
        gamma.close()
        clob.close()
