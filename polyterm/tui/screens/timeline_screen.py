"""TUI Screen for Event Timeline"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_timeline_screen(console: Console):
    """Event timeline screen"""
    console.print()
    console.print(Panel("[bold]Event Timeline[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Visual timeline of upcoming market resolutions[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Next 7 days")
    console.print("  [yellow]2.[/yellow] Next 30 days")
    console.print("  [yellow]3.[/yellow] Next 90 days")
    console.print("  [yellow]4.[/yellow] Bookmarked markets only")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="2"
    )

    if choice == "b":
        return

    if choice == "1":
        console.print()
        subprocess.run(["polyterm", "timeline", "--days", "7"])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "timeline", "--days", "30"])

    elif choice == "3":
        console.print()
        subprocess.run(["polyterm", "timeline", "--days", "90"])

    elif choice == "4":
        console.print()
        subprocess.run(["polyterm", "timeline", "--bookmarked"])
