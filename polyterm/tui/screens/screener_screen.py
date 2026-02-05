"""TUI Screen for Market Screener"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_screener_screen(console: Console):
    """Market screener screen"""
    console.print()
    console.print(Panel("[bold]Market Screener[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Filter markets by multiple criteria[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Interactive mode (recommended)")
    console.print("  [yellow]2.[/yellow] Quick scan - high volume markets")
    console.print("  [yellow]3.[/yellow] Quick scan - big movers")
    console.print("  [yellow]4.[/yellow] Quick scan - ending soon")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "1":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "screener", "-i"])
    elif choice == "2":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "screener", "-v", "10000", "-s", "volume"])
    elif choice == "3":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "screener", "--min-change", "5", "-s", "change"])
    elif choice == "4":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "screener", "--ending-within", "7", "-s", "end_date"])
