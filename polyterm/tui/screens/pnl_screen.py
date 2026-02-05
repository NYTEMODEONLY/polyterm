"""TUI Screen for P&L Tracker"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_pnl_screen(console: Console):
    """P&L tracker screen"""
    console.print()
    console.print(Panel("[bold]P&L Tracker[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Track your profit & loss over time[/bold]")
    console.print()
    console.print("[cyan]Time Period:[/cyan]")
    console.print("  [yellow]1.[/yellow] Today")
    console.print("  [yellow]2.[/yellow] Last 7 days")
    console.print("  [yellow]3.[/yellow] Last 30 days")
    console.print("  [yellow]4.[/yellow] Last year")
    console.print("  [yellow]5.[/yellow] All time")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select period[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="3"
    )

    if choice == "b":
        return

    periods = {"1": "day", "2": "week", "3": "month", "4": "year", "5": "all"}
    period = periods.get(choice, "month")

    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pnl", "--period", period, "--detailed"])
