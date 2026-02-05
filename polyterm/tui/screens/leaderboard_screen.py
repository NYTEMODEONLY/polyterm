"""TUI Screen for Leaderboard"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_leaderboard_screen(console: Console):
    """Leaderboard screen"""
    console.print()
    console.print(Panel("[bold]Trader Leaderboard[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]See top traders and your ranking[/bold]")
    console.print()
    console.print("[cyan]Leaderboard Type:[/cyan]")
    console.print("  [yellow]1.[/yellow] Top by Profit")
    console.print("  [yellow]2.[/yellow] Top by Volume")
    console.print("  [yellow]3.[/yellow] Top by Win Rate")
    console.print("  [yellow]4.[/yellow] Most Active")
    console.print("  [yellow]5.[/yellow] My Ranking")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "5":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "leaderboard", "--me"])
        return

    type_map = {
        "1": "profit",
        "2": "volume",
        "3": "winrate",
        "4": "active",
    }

    board_type = type_map.get(choice, "profit")

    # Get period
    console.print("[cyan]Time Period:[/cyan]")
    console.print("  [yellow]1.[/yellow] 24 hours")
    console.print("  [yellow]2.[/yellow] 7 days")
    console.print("  [yellow]3.[/yellow] 30 days")
    console.print("  [yellow]4.[/yellow] All time")
    console.print()

    period_choice = Prompt.ask(
        "[cyan]Select period[/cyan]",
        choices=["1", "2", "3", "4"],
        default="2"
    )

    period_map = {"1": "24h", "2": "7d", "3": "30d", "4": "all"}
    period = period_map.get(period_choice, "7d")

    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "leaderboard", "-t", board_type, "-p", period])
