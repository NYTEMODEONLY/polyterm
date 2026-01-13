"""Profit & Loss Tracker - Track your P&L over time"""

import click
from datetime import datetime, timedelta
from collections import defaultdict
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--period", "-p", type=click.Choice(["day", "week", "month", "year", "all"]), default="month", help="Time period")
@click.option("--detailed", "-d", is_flag=True, help="Show detailed breakdown")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def pnl(ctx, period, detailed, output_format):
    """Track your profit & loss over time

    Analyzes closed positions to show your trading performance.

    Examples:
        polyterm pnl                   # Last month P&L
        polyterm pnl --period week     # Last week
        polyterm pnl --period year     # Last year
        polyterm pnl --detailed        # Show each trade
    """
    console = Console()
    db = Database()

    # Get date range
    now = datetime.now()
    if period == "day":
        start_date = now - timedelta(days=1)
        period_label = "Today"
    elif period == "week":
        start_date = now - timedelta(days=7)
        period_label = "Last 7 Days"
    elif period == "month":
        start_date = now - timedelta(days=30)
        period_label = "Last 30 Days"
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
            print_json({'success': True, 'period': period, 'trades': 0, 'pnl': 0})
        else:
            console.print("[yellow]No closed positions in this period.[/yellow]")
            console.print("[dim]Close positions with 'polyterm position --close <id>'[/dim]")
        return

    # Calculate P&L metrics
    metrics = _calculate_pnl_metrics(filtered)

    if output_format == 'json':
        print_json({
            'success': True,
            'period': period,
            'period_label': period_label,
            'metrics': metrics,
        })
        return

    # Display results
    console.print()
    console.print(Panel(f"[bold]P&L Report: {period_label}[/bold]", border_style="cyan"))
    console.print()

    # Summary
    console.print("[bold]Summary:[/bold]")

    pnl_color = "green" if metrics['total_pnl'] >= 0 else "red"
    console.print(f"  Total P&L: [{pnl_color}]${metrics['total_pnl']:+,.2f}[/{pnl_color}]")
    console.print(f"  ROI: [{pnl_color}]{metrics['roi']:+.1%}[/{pnl_color}]")
    console.print()

    # Win/Loss breakdown
    console.print("[bold]Performance:[/bold]")
    perf_table = Table(show_header=False, box=None, padding=(0, 2))
    perf_table.add_column(width=15)
    perf_table.add_column(justify="right")

    perf_table.add_row("Total Trades", str(metrics['total_trades']))
    perf_table.add_row("Wins", f"[green]{metrics['wins']}[/green]")
    perf_table.add_row("Losses", f"[red]{metrics['losses']}[/red]")
    perf_table.add_row("Win Rate", f"{metrics['win_rate']:.1%}")
    perf_table.add_row("Avg Win", f"[green]+${metrics['avg_win']:.2f}[/green]")
    perf_table.add_row("Avg Loss", f"[red]-${metrics['avg_loss']:.2f}[/red]")
    perf_table.add_row("Profit Factor", f"{metrics['profit_factor']:.2f}")

    console.print(perf_table)
    console.print()

    # P&L Chart
    console.print("[bold]P&L Trend:[/bold]")
    _display_pnl_chart(console, filtered)
    console.print()

    # Daily breakdown (if detailed or period is day/week)
    if detailed or period in ['day', 'week']:
        console.print("[bold]Trade Details:[/bold]")
        console.print()

        detail_table = Table(show_header=True, header_style="bold cyan", box=None)
        detail_table.add_column("Date", width=10)
        detail_table.add_column("Market", max_width=30)
        detail_table.add_column("Side", width=5)
        detail_table.add_column("P&L", width=12, justify="right")

        for pos in sorted(filtered, key=lambda x: x.get('exit_date', ''), reverse=True)[:15]:
            try:
                exit_date = datetime.fromisoformat(pos['exit_date']).strftime("%m/%d")
            except Exception:
                exit_date = "?"

            trade_pnl = _calculate_position_pnl(pos)
            pnl_str = f"[green]+${trade_pnl:.2f}[/green]" if trade_pnl >= 0 else f"[red]${trade_pnl:.2f}[/red]"
            side_str = f"[green]YES[/green]" if pos['side'] == 'yes' else f"[red]NO[/red]"

            detail_table.add_row(
                exit_date,
                pos['title'][:28],
                side_str,
                pnl_str,
            )

        console.print(detail_table)
        console.print()

    # Streaks
    console.print("[bold]Streaks:[/bold]")
    console.print(f"  Current: {_format_streak(metrics['current_streak'])}")
    console.print(f"  Best Win Streak: [green]{metrics['best_win_streak']}[/green]")
    console.print(f"  Worst Loss Streak: [red]{metrics['worst_loss_streak']}[/red]")
    console.print()


def _calculate_position_pnl(pos: dict) -> float:
    """Calculate P&L for a single position"""
    entry = pos.get('entry_price', 0)
    exit_price = pos.get('exit_price', 0)
    shares = pos.get('shares', 0)
    side = pos.get('side', 'yes')

    if side == 'yes':
        return (exit_price - entry) * shares
    else:
        return (entry - exit_price) * shares


def _calculate_pnl_metrics(positions: list) -> dict:
    """Calculate P&L metrics from positions"""
    pnls = [_calculate_position_pnl(p) for p in positions]
    costs = []

    for pos in positions:
        entry = pos.get('entry_price', 0)
        shares = pos.get('shares', 0)
        if pos.get('side') == 'yes':
            costs.append(entry * shares)
        else:
            costs.append((1 - entry) * shares)

    total_pnl = sum(pnls)
    total_cost = sum(costs) if costs else 1
    roi = total_pnl / total_cost if total_cost > 0 else 0

    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]

    win_rate = len(wins) / len(pnls) if pnls else 0
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = abs(sum(losses) / len(losses)) if losses else 0

    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

    # Calculate streaks
    current_streak = 0
    best_win_streak = 0
    worst_loss_streak = 0
    temp_win = 0
    temp_loss = 0

    for p in pnls:
        if p > 0:
            temp_win += 1
            temp_loss = 0
            best_win_streak = max(best_win_streak, temp_win)
        elif p < 0:
            temp_loss += 1
            temp_win = 0
            worst_loss_streak = max(worst_loss_streak, temp_loss)

    # Current streak
    if pnls:
        last_pnl = pnls[-1]
        for p in reversed(pnls):
            if (p > 0) == (last_pnl > 0):
                current_streak += 1 if last_pnl > 0 else -1
            else:
                break

    return {
        'total_pnl': total_pnl,
        'roi': roi,
        'total_trades': len(pnls),
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': profit_factor,
        'current_streak': current_streak,
        'best_win_streak': best_win_streak,
        'worst_loss_streak': worst_loss_streak,
    }


def _display_pnl_chart(console: Console, positions: list):
    """Display cumulative P&L chart"""
    if not positions:
        return

    # Sort by exit date
    sorted_pos = sorted(positions, key=lambda x: x.get('exit_date', ''))

    # Calculate cumulative P&L
    cumulative = []
    running = 0
    for pos in sorted_pos:
        pnl = _calculate_position_pnl(pos)
        running += pnl
        cumulative.append(running)

    if not cumulative:
        return

    # Normalize for chart
    min_pnl = min(cumulative)
    max_pnl = max(cumulative)
    range_pnl = max_pnl - min_pnl if max_pnl != min_pnl else 1

    chart_width = 40
    chart_height = 6

    # Create chart
    chart = []
    for row in range(chart_height):
        line = ""
        threshold = max_pnl - (row / (chart_height - 1)) * range_pnl

        for i, val in enumerate(cumulative[-chart_width:]):
            if val >= threshold:
                if val >= 0:
                    line += "[green]█[/green]"
                else:
                    line += "[red]█[/red]"
            else:
                line += " "

        chart.append(line)

    # Display
    for line in chart:
        console.print(f"  |{line}")

    console.print(f"  +{'-' * chart_width}")
    console.print(f"  [dim]← oldest{' ' * (chart_width - 14)}newest →[/dim]")


def _format_streak(streak: int) -> str:
    """Format streak for display"""
    if streak > 0:
        return f"[green]{streak}W[/green]"
    elif streak < 0:
        return f"[red]{abs(streak)}L[/red]"
    else:
        return "[dim]0[/dim]"
