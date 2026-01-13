"""TUI Screen for Exit Strategy Planner"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_exit_screen(console: Console):
    """Exit strategy planner screen"""
    console.print()
    console.print(Panel("[bold]Exit Strategy Planner[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Plan your profit targets and stop losses[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Plan exit for a position")
    console.print("  [yellow]2.[/yellow] View saved exit plans")
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
        subprocess.run(["polyterm", "exit", "--interactive"])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "exit", "--list"])
