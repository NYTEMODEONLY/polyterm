"""TUI Screen for Odds Converter"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_odds_screen(console: Console):
    """Odds converter screen"""
    console.print()
    console.print(Panel("[bold]Odds Converter[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Convert between probability and betting odds formats[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Convert probability (e.g., 0.65)")
    console.print("  [yellow]2.[/yellow] Convert decimal odds (e.g., 2.5)")
    console.print("  [yellow]3.[/yellow] Convert American odds (e.g., +150)")
    console.print("  [yellow]4.[/yellow] Get odds from market")
    console.print("  [yellow]5.[/yellow] Interactive mode")
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
        value = Prompt.ask("[cyan]Enter probability (e.g., 0.65 or 65%)[/cyan]")
        if value:
            subprocess.run(["polyterm", "odds", value])

    elif choice == "2":
        console.print()
        value = Prompt.ask("[cyan]Enter decimal odds (e.g., 2.5)[/cyan]")
        if value:
            subprocess.run(["polyterm", "odds", value, "--from", "decimal"])

    elif choice == "3":
        console.print()
        value = Prompt.ask("[cyan]Enter American odds (e.g., +150)[/cyan]")
        if value:
            subprocess.run(["polyterm", "odds", value, "--from", "american"])

    elif choice == "4":
        console.print()
        market = Prompt.ask("[cyan]Enter market name[/cyan]")
        if market:
            subprocess.run(["polyterm", "odds", "--market", market])

    elif choice == "5":
        console.print()
        subprocess.run(["polyterm", "odds", "-i"])
