"""Performance Attribution - Understand what's working in your trading"""

import click
from collections import defaultdict
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--period", "-p", type=click.Choice(["week", "month", "quarter", "year", "all"]), default="month", help="Time period")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def attribution(ctx, period, output_format):
    """Analyze what's driving your trading performance

    Breaks down P&L by:
    - Category (crypto, politics, sports, etc.)
    - Side (YES vs NO positions)
    - Position size (small, medium, large)
    - Hold time (quick trades vs long holds)

    Examples:
        polyterm attribution                   # Last month
        polyterm attribution --period quarter  # Last quarter
        polyterm attribution --period all      # All time
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Get date range
    now = datetime.now()
    if period == "week":
        start_date = now - timedelta(days=7)
        period_label = "Last Week"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_label = "Last Month"
    elif period == "quarter":
        start_date = now - timedelta(days=90)
        period_label = "Last Quarter"
    elif period == "year":
        start_date = now - timedelta(days=365)
        period_label = "Last Year"
    else:
        start_date = datetime(2020, 1, 1)
        period_label = "All Time"

    # Get closed positions
    positions = db.get_positions(status='closed')

    # Filter by date
    filtered = []
    for pos in positions:
        try:
            exit_date = datetime.fromisoformat(pos['exit_date'])
            if exit_date >= start_date:
                filtered.append(pos)
        except Exception:
            continue

    if not filtered:
        if output_format == 'json':
            print_json({'success': True, 'period': period, 'message': 'No closed positions'})
        else:
            console.print("[yellow]No closed positions in this period.[/yellow]")
        return

    # Enrich with category data
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        enriched = []
        for pos in filtered:
            # Try to get category
            category = 'Unknown'
            try:
                markets = gamma_client.search_markets(pos['market_id'], limit=1)
                if markets:
                    category = markets[0].get('category', 'Unknown')
            except Exception:
                pass

            # Calculate P&L
            entry = pos.get('entry_price', 0)
            exit_price = pos.get('exit_price', 0)
            shares = pos.get('shares', 0)
            side = pos.get('side', 'yes')

            if side == 'yes':
                pnl = (exit_price - entry) * shares
                cost = entry * shares
            else:
                pnl = (entry - exit_price) * shares
                cost = (1 - entry) * shares

            # Calculate hold time
            try:
                entry_date = datetime.fromisoformat(pos['entry_date'])
                exit_date = datetime.fromisoformat(pos['exit_date'])
                hold_days = (exit_date - entry_date).days
            except Exception:
                hold_days = 0

            enriched.append({
                'position': pos,
                'category': category,
                'pnl': pnl,
                'cost': cost,
                'side': side,
                'hold_days': hold_days,
            })

    finally:
        gamma_client.close()

    # Calculate attributions
    attr = _calculate_attribution(enriched)

    if output_format == 'json':
        print_json({
            'success': True,
            'period': period,
            'period_label': period_label,
            'attribution': attr,
        })
        return

    # Display results
    console.print()
    console.print(Panel(f"[bold]Performance Attribution: {period_label}[/bold]", border_style="cyan"))
    console.print()

    # Summary
    total_pnl = sum(e['pnl'] for e in enriched)
    total_cost = sum(e['cost'] for e in enriched)
    roi = total_pnl / total_cost if total_cost > 0 else 0

    pnl_color = "green" if total_pnl >= 0 else "red"
    console.print(f"[bold]Total P&L:[/bold] [{pnl_color}]${total_pnl:+,.2f}[/{pnl_color}] ({roi:+.1%} ROI)")
    console.print(f"[bold]Trades:[/bold] {len(enriched)}")
    console.print()

    # By Category
    console.print("[bold]By Category:[/bold]")
    console.print()
    _display_attribution_table(console, attr['by_category'])
    console.print()

    # By Side
    console.print("[bold]By Side:[/bold]")
    console.print()
    _display_attribution_table(console, attr['by_side'])
    console.print()

    # By Size
    console.print("[bold]By Position Size:[/bold]")
    console.print()
    _display_attribution_table(console, attr['by_size'])
    console.print()

    # By Hold Time
    console.print("[bold]By Hold Time:[/bold]")
    console.print()
    _display_attribution_table(console, attr['by_hold_time'])
    console.print()

    # Insights
    console.print("[bold]Key Insights:[/bold]")
    _display_insights(console, attr, enriched)
    console.print()


def _calculate_attribution(enriched: list) -> dict:
    """Calculate performance attribution by different dimensions"""

    def calc_stats(items):
        if not items:
            return {'pnl': 0, 'trades': 0, 'win_rate': 0, 'avg_pnl': 0}

        pnl = sum(i['pnl'] for i in items)
        trades = len(items)
        wins = sum(1 for i in items if i['pnl'] > 0)
        win_rate = wins / trades if trades > 0 else 0
        avg_pnl = pnl / trades if trades > 0 else 0

        return {
            'pnl': pnl,
            'trades': trades,
            'win_rate': win_rate,
            'avg_pnl': avg_pnl,
        }

    # By Category
    by_cat = defaultdict(list)
    for e in enriched:
        by_cat[e['category']].append(e)

    by_category = {}
    for cat, items in by_cat.items():
        by_category[cat] = calc_stats(items)

    # By Side
    by_side_data = defaultdict(list)
    for e in enriched:
        by_side_data[e['side'].upper()].append(e)

    by_side = {}
    for side, items in by_side_data.items():
        by_side[side] = calc_stats(items)

    # By Size (small < $100, medium < $500, large >= $500)
    by_size_data = defaultdict(list)
    for e in enriched:
        cost = e['cost']
        if cost < 100:
            size_cat = 'Small (<$100)'
        elif cost < 500:
            size_cat = 'Medium ($100-500)'
        else:
            size_cat = 'Large (>$500)'
        by_size_data[size_cat].append(e)

    by_size = {}
    for size, items in by_size_data.items():
        by_size[size] = calc_stats(items)

    # By Hold Time
    by_hold_data = defaultdict(list)
    for e in enriched:
        days = e['hold_days']
        if days <= 1:
            hold_cat = 'Day Trade (<=1d)'
        elif days <= 7:
            hold_cat = 'Short (2-7d)'
        elif days <= 30:
            hold_cat = 'Medium (1-4w)'
        else:
            hold_cat = 'Long (>1m)'
        by_hold_data[hold_cat].append(e)

    by_hold_time = {}
    for hold, items in by_hold_data.items():
        by_hold_time[hold] = calc_stats(items)

    return {
        'by_category': by_category,
        'by_side': by_side,
        'by_size': by_size,
        'by_hold_time': by_hold_time,
    }


def _display_attribution_table(console: Console, data: dict):
    """Display attribution breakdown table"""
    if not data:
        console.print("[dim]No data[/dim]")
        return

    # Sort by P&L
    sorted_data = sorted(data.items(), key=lambda x: x[1]['pnl'], reverse=True)

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("", width=18)
    table.add_column("P&L", width=12, justify="right")
    table.add_column("Trades", width=8, justify="center")
    table.add_column("Win Rate", width=10, justify="center")
    table.add_column("Avg P&L", width=10, justify="right")

    for name, stats in sorted_data:
        pnl = stats['pnl']
        pnl_str = f"[green]+${pnl:,.0f}[/green]" if pnl >= 0 else f"[red]${pnl:,.0f}[/red]"

        win_rate = stats['win_rate']
        if win_rate >= 0.6:
            wr_str = f"[green]{win_rate:.0%}[/green]"
        elif win_rate >= 0.4:
            wr_str = f"[yellow]{win_rate:.0%}[/yellow]"
        else:
            wr_str = f"[red]{win_rate:.0%}[/red]"

        avg_pnl = stats['avg_pnl']
        avg_str = f"+${avg_pnl:.0f}" if avg_pnl >= 0 else f"${avg_pnl:.0f}"

        table.add_row(
            name[:16],
            pnl_str,
            str(stats['trades']),
            wr_str,
            avg_str,
        )

    console.print(table)


def _display_insights(console: Console, attr: dict, enriched: list):
    """Display key insights from attribution analysis"""
    insights = []

    # Best category
    if attr['by_category']:
        best_cat = max(attr['by_category'].items(), key=lambda x: x[1]['pnl'])
        if best_cat[1]['pnl'] > 0:
            insights.append(f"[green]+[/green] Best category: {best_cat[0]} (+${best_cat[1]['pnl']:,.0f})")

        worst_cat = min(attr['by_category'].items(), key=lambda x: x[1]['pnl'])
        if worst_cat[1]['pnl'] < 0:
            insights.append(f"[red]-[/red] Worst category: {worst_cat[0]} (${worst_cat[1]['pnl']:,.0f})")

    # Side comparison
    if 'YES' in attr['by_side'] and 'NO' in attr['by_side']:
        yes_wr = attr['by_side']['YES']['win_rate']
        no_wr = attr['by_side']['NO']['win_rate']

        if yes_wr > no_wr + 0.1:
            insights.append(f"[green]+[/green] YES positions performing better ({yes_wr:.0%} vs {no_wr:.0%})")
        elif no_wr > yes_wr + 0.1:
            insights.append(f"[green]+[/green] NO positions performing better ({no_wr:.0%} vs {yes_wr:.0%})")

    # Size analysis
    if attr['by_size']:
        best_size = max(attr['by_size'].items(), key=lambda x: x[1]['win_rate'] if x[1]['trades'] >= 3 else 0)
        if best_size[1]['trades'] >= 3:
            insights.append(f"[dim]~[/dim] Best size bracket: {best_size[0]} ({best_size[1]['win_rate']:.0%} win rate)")

    # Hold time
    if attr['by_hold_time']:
        best_hold = max(attr['by_hold_time'].items(), key=lambda x: x[1]['avg_pnl'] if x[1]['trades'] >= 2 else -999)
        if best_hold[1]['trades'] >= 2 and best_hold[1]['avg_pnl'] > 0:
            insights.append(f"[dim]~[/dim] Best hold strategy: {best_hold[0]} (+${best_hold[1]['avg_pnl']:.0f} avg)")

    if not insights:
        console.print("  [dim]Not enough data for insights[/dim]")
    else:
        for insight in insights:
            console.print(f"  {insight}")
