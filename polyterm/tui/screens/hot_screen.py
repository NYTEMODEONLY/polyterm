"""TUI Screen for Hot Markets"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_hot_screen(console: Console):
    """Hot markets screen"""
    console.print()
    console.print(Panel("[bold]Hot Markets[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]See what markets are moving right now[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Top movers (all)")
    console.print("  [yellow]2.[/yellow] Gainers only")
    console.print("  [yellow]3.[/yellow] Losers only")
    console.print("  [yellow]4.[/yellow] Highest volume")
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
        subprocess.run(["polyterm", "hot"])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "hot", "--gainers"])

    elif choice == "3":
        console.print()
        subprocess.run(["polyterm", "hot", "--losers"])

    elif choice == "4":
        console.print()
        subprocess.run(["polyterm", "hot", "--volume"])
