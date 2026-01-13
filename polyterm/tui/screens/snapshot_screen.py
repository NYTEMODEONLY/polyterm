"""TUI Screen for Market Snapshots"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_snapshot_screen(console: Console):
    """Market snapshot screen"""
    console.print()
    console.print(Panel("[bold]Market Snapshots[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Save and compare market states over time[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] List saved snapshots")
    console.print("  [yellow]2.[/yellow] Save new snapshot")
    console.print("  [yellow]3.[/yellow] View snapshot details")
    console.print("  [yellow]4.[/yellow] Compare snapshot to current")
    console.print("  [yellow]5.[/yellow] Delete snapshot")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        console.print()
        subprocess.run(["polyterm", "snapshot", "--list"])

    elif choice == "2":
        console.print()
        market = Prompt.ask("[cyan]Market to snapshot[/cyan]")
        if market:
            subprocess.run(["polyterm", "snapshot", "--save", market])

    elif choice == "3":
        console.print()
        snap_id = Prompt.ask("[cyan]Snapshot ID[/cyan]")
        if snap_id:
            subprocess.run(["polyterm", "snapshot", "--view", snap_id])

    elif choice == "4":
        console.print()
        snap_id = Prompt.ask("[cyan]Snapshot ID to compare[/cyan]")
        if snap_id:
            subprocess.run(["polyterm", "snapshot", "--compare", snap_id])

    elif choice == "5":
        console.print()
        snap_id = Prompt.ask("[cyan]Snapshot ID to delete[/cyan]")
        if snap_id:
            subprocess.run(["polyterm", "snapshot", "--delete", snap_id])
