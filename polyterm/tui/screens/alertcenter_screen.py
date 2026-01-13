"""TUI Screen for Alert Center"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_alertcenter_screen(console: Console):
    """Alert center screen"""
    console.print()
    console.print(Panel("[bold]Alert Center[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Unified view of all alerts and notifications[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] View active alerts")
    console.print("  [yellow]2.[/yellow] Check for new alerts")
    console.print("  [yellow]3.[/yellow] View all (incl. acknowledged)")
    console.print("  [yellow]4.[/yellow] Clear all alerts")
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
        subprocess.run(["polyterm", "center"])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "center", "--check"])

    elif choice == "3":
        console.print()
        subprocess.run(["polyterm", "center", "--all"])

    elif choice == "4":
        console.print()
        subprocess.run(["polyterm", "center", "--clear"])
