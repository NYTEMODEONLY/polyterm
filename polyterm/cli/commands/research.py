"""Research command - flagship agent-native market research brief."""

import click
from rich.console import Console
from rich.panel import Panel

from ...api.clob import CLOBClient
from ...api.gamma import GammaClient
from ...core.market_research import MarketResearchEngine
from ...core.trade_thesis import TradeThesisEngine
from ...db.database import Database
from ...utils.errors import handle_api_error
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", required=True, help="Market slug, URL, Gamma ID, condition ID, or search term")
@click.option("--prefetch-whales", is_flag=True, help="Run live whale lookup first to enrich local evidence")
@click.option("--min-notional", default=100000.0, show_default=True, type=float, help="Minimum whale trade notional")
@click.option("--hours", default=72, show_default=True, type=int, help="Whale activity lookback window")
@click.option("--limit", default=5, show_default=True, type=int, help="Displayed whale result limit")
@click.option("--brief", is_flag=True, help="Show compact human output")
@click.option("--persist", is_flag=True, help="Persist this research brief to the local archive")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def research(ctx, market, prefetch_whales, min_notional, hours, limit, brief, persist, output_format):
    """Generate a flagship agent-native market research brief"""
    config = ctx.obj["config"]
    console = Console()
    gamma = GammaClient(base_url=config.gamma_base_url, api_key=config.gamma_api_key)
    clob = CLOBClient(rest_endpoint=config.clob_rest_endpoint, ws_endpoint=config.clob_endpoint)

    try:
        database = Database()
        thesis_engine = TradeThesisEngine(gamma_client=gamma, clob_client=clob, database=database)
        engine = MarketResearchEngine(thesis_engine=thesis_engine, database=database)
        result = engine.build(
            market,
            prefetch_whales=prefetch_whales,
            min_notional=min_notional,
            hours=hours,
            limit=limit,
            persist=persist,
        )

        if output_format == "json":
            print_json({"success": True, "research": result})
            return

        market_info = result["market"]
        brief_info = result["brief"]
        console.print(
            Panel(
                f"[bold]{market_info.get('title') or market}[/bold]\n"
                f"Recommendation: [cyan]{brief_info['recommendation']}[/cyan]\n"
                f"Direction: [cyan]{brief_info['direction'].upper()}[/cyan]\n"
                f"Confidence: [cyan]{brief_info['confidence']:.0%}[/cyan]\n"
                f"{brief_info['headline']}",
                title="Market Research",
                border_style="cyan",
            )
        )

        console.print("[bold]Key Evidence[/bold]")
        for item in brief_info["key_evidence"][:3 if brief else None]:
            console.print(f"  + {item}")

        if brief_info["key_risks"]:
            console.print("\n[bold red]Key Risks[/bold red]")
            for item in brief_info["key_risks"][:3 if brief else None]:
                console.print(f"  ! {item}")

        if not brief:
            console.print("\n[bold]Next Actions[/bold]")
            for item in brief_info["next_actions"]:
                console.print(f"  - {item}")
            if result["quality_flags"]:
                console.print(f"\n[dim]Quality flags: {', '.join(result['quality_flags'])}[/dim]")

    except Exception as exc:
        if output_format == "json":
            print_json({"success": False, "error": str(exc)})
        else:
            handle_api_error(console, exc, "market research")
    finally:
        gamma.close()
        clob.close()
