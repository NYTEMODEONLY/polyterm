"""Streak Tracker - Track your winning and losing streaks"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--detailed", "-d", is_flag=True, help="Show detailed streak history")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def streak(ctx, detailed, output_format):
    """Track your winning and losing streaks

    Understand your trading patterns and psychology.
    See current streak, best/worst streaks, and patterns.

    Examples:
        polyterm streak              # Current streak status
        polyterm streak --detailed   # Full streak history
    """
    console = Console()
    db = Database()

    # Get closed positions
    positions = db.get_positions(status='closed')

    if not positions:
        if output_format == 'json':
            print_json({'success': True, 'message': 'No closed positions'})
        else:
            console.print()
            console.print(Panel("[bold]Streak Tracker[/bold]", border_style="cyan"))
            console.print()
            console.print("[yellow]No closed positions to analyze.[/yellow]")
            console.print("[dim]Track positions with 'polyterm position' to see streaks.[/dim]")
        return

    # Sort by exit date
    sorted_positions = []
    for pos in positions:
        try:
            exit_date = datetime.fromisoformat(pos['exit_date'])
            sorted_positions.append((exit_date, pos))
        except Exception:
            continue

    sorted_positions.sort(key=lambda x: x[0])
    positions = [p[1] for p in sorted_positions]

    # Calculate streaks
    streak_data = _calculate_streaks(positions)

    if output_format == 'json':
        print_json({
            'success': True,
            'current_streak': streak_data['current'],
            'best_win_streak': streak_data['best_win'],
            'worst_loss_streak': streak_data['worst_loss'],
            'statistics': streak_data['stats'],
        })
        return

    # Display
    console.print()
    console.print(Panel("[bold]Streak Tracker[/bold]", border_style="cyan"))
    console.print()

    # Current streak
    current = streak_data['current']
    if current['type'] == 'win':
        streak_icon = "🔥"
        streak_color = "green"
        streak_msg = f"You're on a [green]{current['count']}-win streak![/green]"
    elif current['type'] == 'loss':
        streak_icon = "❄️"
        streak_color = "red"
        streak_msg = f"You're on a [red]{current['count']}-loss streak[/red]"
    else:
        streak_icon = "➖"
        streak_color = "yellow"
        streak_msg = "[yellow]No current streak[/yellow]"

    console.print(f"[bold]Current:[/bold] {streak_icon} {streak_msg}")
    console.print()

    # Best/Worst
    console.print("[bold]Records:[/bold]")
    console.print()

    records_table = Table(show_header=False, box=None, padding=(0, 2))
    records_table.add_column(width=20)
    records_table.add_column(width=10, justify="center")
    records_table.add_column(width=25)

    best = streak_data['best_win']
    records_table.add_row(
        "Best Win Streak",
        f"[green]{best['count']}[/green]",
        f"[dim]{best['period']}[/dim]" if best['period'] else "",
    )

    worst = streak_data['worst_loss']
    records_table.add_row(
        "Worst Loss Streak",
        f"[red]{worst['count']}[/red]",
        f"[dim]{worst['period']}[/dim]" if worst['period'] else "",
    )

    console.print(records_table)
    console.print()

    # Statistics
    stats = streak_data['stats']
    console.print("[bold]Streak Statistics:[/bold]")
    console.print()

    stats_table = Table(show_header=False, box=None, padding=(0, 2))
    stats_table.add_column(width=25)
    stats_table.add_column(width=15, justify="right")

    stats_table.add_row("Average Win Streak", f"{stats['avg_win_streak']:.1f}")
    stats_table.add_row("Average Loss Streak", f"{stats['avg_loss_streak']:.1f}")
    stats_table.add_row("Total Trades", str(stats['total_trades']))
    stats_table.add_row("Win Rate", f"{stats['win_rate']:.0%}")

    console.print(stats_table)
    console.print()

    # Streak history
    if detailed:
        console.print("[bold]Recent Streak History:[/bold]")
        console.print()

        history = streak_data['history'][-10:]  # Last 10 streaks
        for s in reversed(history):
            if s['type'] == 'win':
                bar = f"[green]{'█' * min(s['count'], 10)}[/green]"
                label = f"+{s['count']}"
            else:
                bar = f"[red]{'█' * min(s['count'], 10)}[/red]"
                label = f"-{s['count']}"

            console.print(f"  {bar} {label}")

        console.print()

    # Psychology tips
    console.print("[bold]Tips:[/bold]")
    _display_tips(console, current, stats)
    console.print()


def _calculate_streaks(positions: list) -> dict:
    """Calculate all streak data"""
    if not positions:
        return {
            'current': {'type': None, 'count': 0},
            'best_win': {'count': 0, 'period': None},
            'worst_loss': {'count': 0, 'period': None},
            'stats': {
                'avg_win_streak': 0,
                'avg_loss_streak': 0,
                'total_trades': 0,
                'win_rate': 0,
            },
            'history': [],
        }

    # Calculate P&L for each position
    results = []
    for pos in positions:
        entry = pos.get('entry_price', 0)
        exit_price = pos.get('exit_price', 0)
        shares = pos.get('shares', 0)
        side = pos.get('side', 'yes')

        if side == 'yes':
            pnl = (exit_price - entry) * shares
        else:
            pnl = (entry - exit_price) * shares

        results.append({
            'position': pos,
            'pnl': pnl,
            'win': pnl > 0,
            'date': pos.get('exit_date', ''),
        })

    # Build streak history
    streaks = []
    current_streak = {'type': None, 'count': 0, 'start': None, 'end': None}

    for r in results:
        result_type = 'win' if r['win'] else 'loss'

        if current_streak['type'] is None:
            current_streak = {'type': result_type, 'count': 1, 'start': r['date'], 'end': r['date']}
        elif current_streak['type'] == result_type:
            current_streak['count'] += 1
            current_streak['end'] = r['date']
        else:
            streaks.append(current_streak)
            current_streak = {'type': result_type, 'count': 1, 'start': r['date'], 'end': r['date']}

    # Add final streak
    if current_streak['type']:
        streaks.append(current_streak)

    # Find best/worst
    win_streaks = [s for s in streaks if s['type'] == 'win']
    loss_streaks = [s for s in streaks if s['type'] == 'loss']

    best_win = max(win_streaks, key=lambda s: s['count']) if win_streaks else {'count': 0}
    worst_loss = max(loss_streaks, key=lambda s: s['count']) if loss_streaks else {'count': 0}

    # Format periods
    if best_win.get('start') and best_win.get('end'):
        try:
            start = datetime.fromisoformat(best_win['start']).strftime("%m/%d")
            end = datetime.fromisoformat(best_win['end']).strftime("%m/%d")
            best_win['period'] = f"{start} - {end}"
        except Exception:
            best_win['period'] = None
    else:
        best_win['period'] = None

    if worst_loss.get('start') and worst_loss.get('end'):
        try:
            start = datetime.fromisoformat(worst_loss['start']).strftime("%m/%d")
            end = datetime.fromisoformat(worst_loss['end']).strftime("%m/%d")
            worst_loss['period'] = f"{start} - {end}"
        except Exception:
            worst_loss['period'] = None
    else:
        worst_loss['period'] = None

    # Current streak is the last one
    current = streaks[-1] if streaks else {'type': None, 'count': 0}

    # Statistics
    avg_win = sum(s['count'] for s in win_streaks) / len(win_streaks) if win_streaks else 0
    avg_loss = sum(s['count'] for s in loss_streaks) / len(loss_streaks) if loss_streaks else 0
    total_trades = len(results)
    wins = sum(1 for r in results if r['win'])
    win_rate = wins / total_trades if total_trades > 0 else 0

    return {
        'current': current,
        'best_win': best_win,
        'worst_loss': worst_loss,
        'stats': {
            'avg_win_streak': avg_win,
            'avg_loss_streak': avg_loss,
            'total_trades': total_trades,
            'win_rate': win_rate,
        },
        'history': streaks,
    }


def _display_tips(console: Console, current: dict, stats: dict):
    """Display psychological tips based on streak status"""
    tips = []

    if current['type'] == 'win' and current['count'] >= 3:
        tips.append("[green]+[/green] Great streak! Stay disciplined - don't let overconfidence lead to risky bets")
        tips.append("[green]+[/green] Consider taking some profit off the table")

    elif current['type'] == 'loss' and current['count'] >= 3:
        tips.append("[red]-[/red] Losing streaks happen to everyone - take a break if frustrated")
        tips.append("[red]-[/red] Reduce position sizes until the streak breaks")
        tips.append("[red]-[/red] Review recent trades - is there a pattern to fix?")

    elif current['type'] == 'loss' and current['count'] >= 5:
        tips.append("[red]![/red] Extended losing streak - strongly consider pausing")
        tips.append("[red]![/red] Review your strategy before continuing")

    else:
        tips.append("[dim]~[/dim] You're trading consistently - keep following your strategy")

    if stats['win_rate'] > 0.6:
        tips.append("[green]+[/green] Strong win rate - your edge is working")
    elif stats['win_rate'] < 0.4:
        tips.append("[yellow]~[/yellow] Low win rate - focus on higher-confidence trades")

    for tip in tips[:3]:
        console.print(f"  {tip}")
