"""TUI Screen for Liquidity Comparison"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_liquidity_screen(console: Console):
    """Liquidity comparison screen"""
    console.print()
    console.print(Panel("[bold]Liquidity Comparison[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Compare liquidity across markets[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] All markets - sort by score")
    console.print("  [yellow]2.[/yellow] All markets - sort by spread")
    console.print("  [yellow]3.[/yellow] Filter by category")
    console.print("  [yellow]4.[/yellow] High volume only (>$10k)")
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
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "liquidity", "-s", "score"])

    elif choice == "2":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "liquidity", "-s", "spread"])

    elif choice == "3":
        category = Prompt.ask("[cyan]Enter category[/cyan]")
        if category:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "liquidity", "-c", category])

    elif choice == "4":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "liquidity", "-v", "10000", "-s", "score"])
