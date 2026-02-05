"""TUI Screen for Trade Journal"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_journal_screen(console: Console):
    """Trade journal screen"""
    console.print()
    console.print(Panel("[bold]Trade Journal[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Document your trades and learn from experience[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] View recent entries")
    console.print("  [yellow]2.[/yellow] Add new entry")
    console.print("  [yellow]3.[/yellow] Search entries")
    console.print("  [yellow]4.[/yellow] View by tag")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "journal", "--list"])

    elif choice == "2":
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "journal", "--add"])

    elif choice == "3":
        query = Prompt.ask("[cyan]Search query[/cyan]", default="")
        if query:
            console.print()
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "journal", "--search", query])

    elif choice == "4":
        tag = Prompt.ask("[cyan]Tag to filter[/cyan]", default="")
        if tag:
            console.print()
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "journal", "--tag", tag])
