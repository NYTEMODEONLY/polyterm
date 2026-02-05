"""Portfolio Analytics - Analyze your portfolio exposure and risk"""

import click
from collections import defaultdict
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command(name="analyze")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def analyze(ctx, output_format):
    """Analyze your portfolio for exposure and risk

    Provides insights on:
    - Category/sector exposure
    - Position concentration
    - Win/loss distribution
    - Correlation analysis
    - Risk metrics

    Examples:
        polyterm analyze              # Full portfolio analysis
        polyterm analyze --format json
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing portfolio...", total=None)

            # Get positions
            positions = db.get_positions(status='open')

            if not positions:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'No open positions found'})
                else:
                    console.print("[yellow]No open positions to analyze.[/yellow]")
                    console.print("[dim]Add positions with 'polyterm position --add'[/dim]")
                return

            # Enrich positions with market data
            enriched = []
            for pos in positions:
                market_data = gamma_client.search_markets(pos['market_id'], limit=1)
                if market_data:
                    market = market_data[0]
                    current_price = _get_price(market)
                    category = market.get('category', 'Unknown')

                    # Calculate current value and P&L
                    if pos['side'] == 'yes':
                        current_value = current_price * pos['shares']
                        cost_basis = pos['entry_price'] * pos['shares']
                    else:
                        current_value = (1 - current_price) * pos['shares']
                        cost_basis = (1 - pos['entry_price']) * pos['shares']

                    unrealized_pnl = current_value - cost_basis

                    enriched.append({
                        'position': pos,
                        'market': market,
                        'current_price': current_price,
                        'current_value': current_value,
                        'cost_basis': cost_basis,
                        'unrealized_pnl': unrealized_pnl,
                        'category': category,
                    })

            if not enriched:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Could not enrich positions'})
                else:
                    console.print("[yellow]Could not fetch market data for positions.[/yellow]")
                return

            # Calculate analytics
            analytics = _calculate_analytics(enriched)

        if output_format == 'json':
            print_json({
                'success': True,
                'analytics': analytics,
            })
            return

        # Display results
        console.print()
        console.print(Panel("[bold]Portfolio Analytics[/bold]", border_style="cyan"))
        console.print()

        # Overview
        console.print("[bold]Portfolio Overview:[/bold]")
        overview_table = Table(show_header=False, box=None, padding=(0, 2))
        overview_table.add_column(width=20)
        overview_table.add_column(justify="right")

        overview_table.add_row("Total Positions", str(analytics['total_positions']))
        overview_table.add_row("Total Cost Basis", f"${analytics['total_cost_basis']:,.2f}")
        overview_table.add_row("Current Value", f"${analytics['total_current_value']:,.2f}")

        pnl_color = "green" if analytics['total_unrealized_pnl'] >= 0 else "red"
        overview_table.add_row(
            "Unrealized P&L",
            f"[{pnl_color}]${analytics['total_unrealized_pnl']:+,.2f} ({analytics['total_pnl_pct']:+.1%})[/{pnl_color}]"
        )

        console.print(overview_table)
        console.print()

        # Category exposure
        console.print("[bold]Category Exposure:[/bold]")
        console.print()
        _display_exposure_chart(console, analytics['category_exposure'])
        console.print()

        # Side distribution
        console.print("[bold]Side Distribution:[/bold]")
        yes_pct = analytics['yes_exposure'] / analytics['total_current_value'] * 100 if analytics['total_current_value'] > 0 else 0
        no_pct = 100 - yes_pct
        console.print(f"  [green]YES[/green]: {yes_pct:.1f}%  |  [red]NO[/red]: {no_pct:.1f}%")
        console.print()

        # Concentration risk
        console.print("[bold]Concentration Risk:[/bold]")
        console.print()

        conc_table = Table(show_header=True, header_style="bold cyan", box=None)
        conc_table.add_column("Position", max_width=40)
        conc_table.add_column("% of Portfolio", width=15, justify="center")
        conc_table.add_column("Value", width=12, justify="right")

        for pos_data in analytics['top_positions'][:5]:
            pct = pos_data['pct_of_portfolio']
            if pct > 30:
                pct_str = f"[red]{pct:.1f}%[/red]"
            elif pct > 20:
                pct_str = f"[yellow]{pct:.1f}%[/yellow]"
            else:
                pct_str = f"{pct:.1f}%"

            conc_table.add_row(
                pos_data['title'][:38],
                pct_str,
                f"${pos_data['value']:,.2f}",
            )

        console.print(conc_table)
        console.print()

        # Risk metrics
        console.print("[bold]Risk Metrics:[/bold]")
        risk_table = Table(show_header=False, box=None, padding=(0, 2))
        risk_table.add_column(width=25)
        risk_table.add_column(justify="right")

        risk_table.add_row("Concentration (HHI)", f"{analytics['hhi_score']:.0f}/10000")
        risk_table.add_row("Max Single Position", f"{analytics['max_position_pct']:.1f}%")
        risk_table.add_row("Avg Position Size", f"${analytics['avg_position_size']:,.2f}")

        # Risk rating
        risk_score = _calculate_risk_score(analytics)
        if risk_score >= 70:
            risk_rating = "[red]High Risk[/red]"
        elif risk_score >= 40:
            risk_rating = "[yellow]Moderate Risk[/yellow]"
        else:
            risk_rating = "[green]Low Risk[/green]"
        risk_table.add_row("Overall Risk", risk_rating)

        console.print(risk_table)
        console.print()

        # Recommendations
        console.print("[bold]Recommendations:[/bold]")
        _display_recommendations(console, analytics)
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)


def _calculate_analytics(enriched: list) -> dict:
    """Calculate portfolio analytics"""
    total_positions = len(enriched)
    total_cost_basis = sum(e['cost_basis'] for e in enriched)
    total_current_value = sum(e['current_value'] for e in enriched)
    total_unrealized_pnl = sum(e['unrealized_pnl'] for e in enriched)
    total_pnl_pct = total_unrealized_pnl / total_cost_basis if total_cost_basis > 0 else 0

    # Category exposure
    category_values = defaultdict(float)
    for e in enriched:
        category_values[e['category']] += e['current_value']

    category_exposure = []
    for cat, value in sorted(category_values.items(), key=lambda x: x[1], reverse=True):
        pct = value / total_current_value * 100 if total_current_value > 0 else 0
        category_exposure.append({'category': cat, 'value': value, 'pct': pct})

    # Side exposure
    yes_exposure = sum(e['current_value'] for e in enriched if e['position']['side'] == 'yes')
    no_exposure = sum(e['current_value'] for e in enriched if e['position']['side'] == 'no')

    # Top positions by value
    top_positions = []
    for e in sorted(enriched, key=lambda x: x['current_value'], reverse=True):
        pct = e['current_value'] / total_current_value * 100 if total_current_value > 0 else 0
        top_positions.append({
            'title': e['position']['title'],
            'value': e['current_value'],
            'pct_of_portfolio': pct,
        })

    # Concentration metrics (Herfindahl-Hirschman Index)
    hhi = sum((e['current_value'] / total_current_value * 100) ** 2 for e in enriched) if total_current_value > 0 else 0

    max_position_pct = max(e['current_value'] / total_current_value * 100 for e in enriched) if total_current_value > 0 else 0
    avg_position_size = total_current_value / total_positions if total_positions > 0 else 0

    return {
        'total_positions': total_positions,
        'total_cost_basis': total_cost_basis,
        'total_current_value': total_current_value,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_pnl_pct': total_pnl_pct,
        'category_exposure': category_exposure,
        'yes_exposure': yes_exposure,
        'no_exposure': no_exposure,
        'top_positions': top_positions,
        'hhi_score': hhi,
        'max_position_pct': max_position_pct,
        'avg_position_size': avg_position_size,
    }


def _display_exposure_chart(console: Console, category_exposure: list):
    """Display category exposure as ASCII bar chart"""
    if not category_exposure:
        console.print("[dim]No category data[/dim]")
        return

    max_pct = max(e['pct'] for e in category_exposure) if category_exposure else 1
    bar_width = 25

    for cat_data in category_exposure[:6]:
        cat = cat_data['category'][:15]
        pct = cat_data['pct']
        bar_len = int((pct / max_pct) * bar_width) if max_pct > 0 else 0

        # Color based on concentration
        if pct > 40:
            color = "red"
        elif pct > 25:
            color = "yellow"
        else:
            color = "cyan"

        bar = f"[{color}]{'█' * bar_len}[/{color}]"
        console.print(f"  {cat:15} {bar} {pct:.1f}%")


def _calculate_risk_score(analytics: dict) -> int:
    """Calculate overall portfolio risk score (0-100)"""
    score = 0

    # Concentration risk
    if analytics['hhi_score'] > 5000:
        score += 40
    elif analytics['hhi_score'] > 2500:
        score += 25
    elif analytics['hhi_score'] > 1500:
        score += 10

    # Max position risk
    if analytics['max_position_pct'] > 50:
        score += 30
    elif analytics['max_position_pct'] > 30:
        score += 20
    elif analytics['max_position_pct'] > 20:
        score += 10

    # Diversification (number of positions)
    if analytics['total_positions'] < 3:
        score += 20
    elif analytics['total_positions'] < 5:
        score += 10

    # Category concentration
    if analytics['category_exposure']:
        top_cat_pct = analytics['category_exposure'][0]['pct']
        if top_cat_pct > 60:
            score += 10
        elif top_cat_pct > 40:
            score += 5

    return min(100, score)


def _display_recommendations(console: Console, analytics: dict):
    """Display portfolio recommendations"""
    recommendations = []

    # Concentration recommendations
    if analytics['max_position_pct'] > 30:
        recommendations.append(
            f"[yellow]![/yellow] Your largest position is {analytics['max_position_pct']:.0f}% of portfolio. Consider reducing exposure."
        )

    if analytics['hhi_score'] > 2500:
        recommendations.append(
            "[yellow]![/yellow] Portfolio is concentrated. Consider diversifying across more markets."
        )

    # Category recommendations
    if analytics['category_exposure'] and analytics['category_exposure'][0]['pct'] > 50:
        cat = analytics['category_exposure'][0]['category']
        recommendations.append(
            f"[yellow]![/yellow] {analytics['category_exposure'][0]['pct']:.0f}% exposure to {cat}. Consider other categories."
        )

    # Side balance
    total = analytics['yes_exposure'] + analytics['no_exposure']
    if total > 0:
        yes_pct = analytics['yes_exposure'] / total
        if yes_pct > 0.8:
            recommendations.append(
                "[yellow]![/yellow] Portfolio heavily weighted to YES. Consider hedging with NO positions."
            )
        elif yes_pct < 0.2:
            recommendations.append(
                "[yellow]![/yellow] Portfolio heavily weighted to NO. May miss upside on positive events."
            )

    # Position count
    if analytics['total_positions'] < 3:
        recommendations.append(
            "[dim]+[/dim] Consider adding more positions to diversify risk."
        )

    # Positive feedback
    if analytics['total_pnl_pct'] > 0.1:
        recommendations.append(
            f"[green]+[/green] Portfolio is up {analytics['total_pnl_pct']:.1%}. Consider taking some profits."
        )

    if not recommendations:
        console.print("  [green]+[/green] Portfolio looks well-balanced!")
    else:
        for rec in recommendations:
            console.print(f"  {rec}")
