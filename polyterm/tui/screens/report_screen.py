"""TUI Screen for Report Generation"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_report_screen(console: Console):
    """Report generation screen"""
    console.print()
    console.print(Panel("[bold]Report Generator[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Generate comprehensive trading reports[/bold]")
    console.print()
    console.print("[cyan]Report Types:[/cyan]")
    console.print("  [yellow]1.[/yellow] Daily Report - market summary")
    console.print("  [yellow]2.[/yellow] Weekly Report - performance review")
    console.print("  [yellow]3.[/yellow] Portfolio Report - your positions")
    console.print("  [yellow]4.[/yellow] Market Report - deep dive on market")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select report type[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "1":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "report", "-t", "daily"])

    elif choice == "2":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "report", "-t", "weekly"])

    elif choice == "3":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "report", "-t", "portfolio"])

    elif choice == "4":
        market = Prompt.ask("[cyan]Enter market name[/cyan]")
        if market:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "report", "-t", "market", "-m", market])
