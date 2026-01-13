"""TUI Screen for Market Notes"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_notes_screen(console: Console):
    """Market notes management screen"""
    console.print()
    console.print(Panel("[bold]Market Notes[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Track your research and thesis on markets[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] List all notes")
    console.print("  [yellow]2.[/yellow] Add/edit note for a market")
    console.print("  [yellow]3.[/yellow] View specific note")
    console.print("  [yellow]4.[/yellow] Delete a note")
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
        # List all notes
        console.print()
        subprocess.run(["polyterm", "notes", "--list"])

    elif choice == "2":
        # Add note
        console.print()
        search = Prompt.ask("[cyan]Search for market[/cyan]", default="")
        if search:
            subprocess.run(["polyterm", "notes", "--add", search])

    elif choice == "3":
        # View note
        console.print()
        search = Prompt.ask("[cyan]Market ID or search term[/cyan]", default="")
        if search:
            subprocess.run(["polyterm", "notes", "--view", search])

    elif choice == "4":
        # Delete note
        console.print()
        market_id = Prompt.ask("[cyan]Market ID to delete note[/cyan]", default="")
        if market_id:
            subprocess.run(["polyterm", "notes", "--delete", market_id])
