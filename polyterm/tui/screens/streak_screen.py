"""TUI Screen for Streak Tracker"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_streak_screen(console: Console):
    """Streak tracker screen"""
    console.print()
    console.print(Panel("[bold]Streak Tracker[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Track your winning and losing streaks[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Current streak status")
    console.print("  [yellow]2.[/yellow] Detailed streak history")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        console.print()
        subprocess.run(["polyterm", "streak"])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "streak", "--detailed"])
