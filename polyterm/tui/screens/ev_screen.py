"""TUI Screen for Expected Value Calculator"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_ev_screen(console: Console):
    """Expected value calculator screen"""
    console.print()
    console.print(Panel("[bold]Expected Value Calculator[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Calculate if a trade has positive expected value[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Interactive mode (recommended)")
    console.print("  [yellow]2.[/yellow] Quick calculation")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "1":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "ev", "-i"])

    elif choice == "2":
        market = Prompt.ask("[cyan]Market name[/cyan]")
        if not market:
            return

        prob = Prompt.ask("[cyan]Your probability (0-1 or %)[/cyan]")
        if not prob:
            return

        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "ev", "-m", market, "-p", prob])
