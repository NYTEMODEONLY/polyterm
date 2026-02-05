"""TUI Screen for Position Tracking"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_position_screen(console: Console):
    """Position tracking management screen"""
    console.print()
    console.print(Panel("[bold]Position Tracker[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Track your trades without connecting a wallet[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] View all positions")
    console.print("  [yellow]2.[/yellow] View open positions only")
    console.print("  [yellow]3.[/yellow] View closed positions")
    console.print("  [yellow]4.[/yellow] Add new position")
    console.print("  [yellow]5.[/yellow] Close a position")
    console.print("  [yellow]6.[/yellow] View P&L summary")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "5", "6", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        # List all positions
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "position", "--list"])

    elif choice == "2":
        # Open positions
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "position", "--list", "--open"])

    elif choice == "3":
        # Closed positions
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "position", "--list", "--closed"])

    elif choice == "4":
        # Add position interactively
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "position", "--interactive"])

    elif choice == "5":
        # Close position
        console.print()
        pos_id = Prompt.ask("[cyan]Position ID to close[/cyan]", default="")
        if pos_id:
            try:
                subprocess.run([sys.executable, "-m", "polyterm.cli.main", "position", "--close", pos_id])
            except ValueError:
                console.print("[red]Invalid position ID[/red]")

    elif choice == "6":
        # P&L summary
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "position", "--summary"])
