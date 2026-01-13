"""TUI Screen for Watchlist Groups"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_groups_screen(console: Console):
    """Watchlist groups screen"""
    console.print()
    console.print(Panel("[bold]Watchlist Groups[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Organize markets into named collections[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] List all groups")
    console.print("  [yellow]2.[/yellow] Create new group")
    console.print("  [yellow]3.[/yellow] View group markets")
    console.print("  [yellow]4.[/yellow] Add market to group")
    console.print("  [yellow]5.[/yellow] Remove market from group")
    console.print("  [yellow]6.[/yellow] Delete group")
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
        console.print()
        subprocess.run(["polyterm", "groups", "--list"])

    elif choice == "2":
        console.print()
        name = Prompt.ask("[cyan]Group name[/cyan]")
        if name:
            subprocess.run(["polyterm", "groups", "--create", name])

    elif choice == "3":
        console.print()
        name = Prompt.ask("[cyan]Group name to view[/cyan]")
        if name:
            subprocess.run(["polyterm", "groups", "--view", name])

    elif choice == "4":
        console.print()
        group = Prompt.ask("[cyan]Group name[/cyan]")
        market = Prompt.ask("[cyan]Market to add[/cyan]")
        if group and market:
            subprocess.run(["polyterm", "groups", "--add", group, "-m", market])

    elif choice == "5":
        console.print()
        group = Prompt.ask("[cyan]Group name[/cyan]")
        market = Prompt.ask("[cyan]Market to remove[/cyan]")
        if group and market:
            subprocess.run(["polyterm", "groups", "--remove", group, "-m", market])

    elif choice == "6":
        console.print()
        name = Prompt.ask("[cyan]Group name to delete[/cyan]")
        if name:
            subprocess.run(["polyterm", "groups", "--delete", name])
