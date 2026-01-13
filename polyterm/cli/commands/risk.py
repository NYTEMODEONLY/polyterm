"""Risk assessment command - Evaluate market risk factors"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...core.risk_score import MarketRiskScorer, RiskAssessment
from ...utils.config import Config
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", default=None, help="Market ID or search term")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def risk(ctx, market, output_format):
    """Assess risk factors for a market

    Evaluates markets on:
    - Resolution clarity (subjective vs objective)
    - Liquidity quality
    - Time to resolution
    - Volume patterns (wash trading indicators)
    - Spread
    - Category risk

    Examples:
        polyterm risk --market "bitcoin"
        polyterm risk -m 0x1234...
    """
    console = Console()
    config = ctx.obj["config"]

    if not market:
        console.print(Panel(
            "[bold]Market Risk Assessment[/bold]\n"
            "[dim]Evaluate a market's risk factors before trading[/dim]",
            style="cyan"
        ))
        console.print()
        market = Prompt.ask("[cyan]Enter market ID or search term[/cyan]")

    if not market:
        console.print("[red]No market specified.[/red]")
        return

    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Search for market if not an ID
        console.print(f"[dim]Searching for market: {market}[/dim]")

        markets = gamma_client.search_markets(market, limit=5)

        if not markets:
            console.print(f"[yellow]No markets found matching '{market}'[/yellow]")
            return

        # If multiple results, let user choose
        if len(markets) > 1 and output_format != 'json':
            console.print()
            console.print("[bold]Multiple markets found:[/bold]")
            for i, m in enumerate(markets, 1):
                title = m.get('question', m.get('title', 'Unknown'))[:60]
                console.print(f"  [cyan]{i}.[/cyan] {title}")

            console.print()
            choice = Prompt.ask(
                "[cyan]Select market number[/cyan]",
                choices=[str(i) for i in range(1, len(markets) + 1)],
                default="1"
            )
            selected_market = markets[int(choice) - 1]
        else:
            selected_market = markets[0]

        # Get detailed market data
        market_id = selected_market.get('id', selected_market.get('condition_id', ''))
        title = selected_market.get('question', selected_market.get('title', 'Unknown'))

        console.print()
        console.print(f"[bold]Analyzing:[/bold] {title[:70]}...")
        console.print()

        # Extract market data for scoring
        description = selected_market.get('description', '')
        end_date_str = selected_market.get('endDate', selected_market.get('end_date_iso', ''))
        end_date = None
        if end_date_str:
            try:
                end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            except Exception:
                pass

        volume_24h = float(selected_market.get('volume24hr', selected_market.get('volume', 0)) or 0)
        liquidity = float(selected_market.get('liquidity', 0) or 0)
        spread = float(selected_market.get('spread', 0) or 0)
        category = selected_market.get('category', '')
        resolution_source = selected_market.get('resolutionSource', '')

        # Score the market
        scorer = MarketRiskScorer()
        assessment = scorer.score_market(
            market_id=market_id,
            title=title,
            description=description,
            end_date=end_date,
            volume_24h=volume_24h,
            liquidity=liquidity,
            spread=spread,
            category=category,
            resolution_source=resolution_source,
        )

        # Output
        if output_format == 'json':
            print_json({
                'success': True,
                'assessment': assessment.to_dict(),
            })
        else:
            _display_assessment(console, assessment, scorer)

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _display_assessment(console: Console, assessment: RiskAssessment, scorer: MarketRiskScorer):
    """Display the risk assessment"""

    # Overall grade panel
    grade_color = scorer.get_grade_color(assessment.overall_grade)
    grade_desc = scorer.get_grade_description(assessment.overall_grade)

    console.print(Panel(
        f"[bold {grade_color}]Grade: {assessment.overall_grade}[/bold {grade_color}]\n"
        f"[{grade_color}]{grade_desc}[/{grade_color}]\n\n"
        f"[dim]Risk Score: {assessment.overall_score}/100 (lower is better)[/dim]",
        title="[bold]Risk Assessment[/bold]",
        border_style=grade_color,
    ))
    console.print()

    # Factor breakdown
    console.print("[bold yellow]Risk Factor Breakdown[/bold yellow]")
    console.print()

    factors_table = Table(show_header=True)
    factors_table.add_column("Factor", style="cyan")
    factors_table.add_column("Score", justify="center", width=8)
    factors_table.add_column("Weight", justify="center", width=8)
    factors_table.add_column("Details")

    for factor_name, factor_data in assessment.factors.items():
        score = factor_data['score']
        weight = factor_data['weight']
        reason = factor_data['reason']

        # Color code the score
        if score <= 30:
            score_style = "green"
        elif score <= 50:
            score_style = "yellow"
        elif score <= 70:
            score_style = "orange1"
        else:
            score_style = "red"

        # Format factor name
        display_name = factor_name.replace('_', ' ').title()

        factors_table.add_row(
            display_name,
            f"[{score_style}]{score}[/{score_style}]",
            f"{weight*100:.0f}%",
            reason,
        )

    console.print(factors_table)
    console.print()

    # Warnings
    if assessment.warnings:
        console.print("[bold red]Warnings[/bold red]")
        for warning in assessment.warnings:
            console.print(f"  [red]![/red] {warning}")
        console.print()

    # Recommendations
    console.print("[bold green]Recommendations[/bold green]")
    for rec in assessment.recommendations:
        console.print(f"  [green]+[/green] {rec}")
    console.print()

    # Legend
    console.print("[dim]Score Guide: 0-30 (Low Risk) | 31-50 (Moderate) | 51-70 (High) | 71+ (Very High)[/dim]")
