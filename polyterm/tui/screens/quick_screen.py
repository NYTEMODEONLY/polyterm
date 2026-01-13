"""TUI Screen for Quick Actions"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_quick_screen(console: Console):
    """Quick actions screen"""
    console.print()
    console.print(Panel("[bold]Quick Actions[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Fast access to common trading tasks[/bold]")
    console.print()
    console.print("[cyan]Actions:[/cyan]")
    console.print("  [yellow]1.[/yellow] Quick price check")
    console.print("  [yellow]2.[/yellow] Quick buy calculation")
    console.print("  [yellow]3.[/yellow] Quick sell calculation")
    console.print("  [yellow]4.[/yellow] Quick market info")
    console.print("  [yellow]5.[/yellow] Quick add to watchlist")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select action[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    market = Prompt.ask("[cyan]Market name[/cyan]")
    if not market:
        return

    action_map = {
        "1": "price",
        "2": "buy",
        "3": "sell",
        "4": "info",
        "5": "watch",
    }

    action = action_map.get(choice, "price")

    console.print()
    subprocess.run(["polyterm", "quick", action, market])
