"""TUI Screen for Pinned Markets"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_pin_screen(console: Console):
    """Pinned markets screen"""
    console.print()
    console.print(Panel("[bold]Pinned Markets[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Quick access to your most important markets[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] View pinned markets")
    console.print("  [yellow]2.[/yellow] Pin a new market")
    console.print("  [yellow]3.[/yellow] Refresh prices")
    console.print("  [yellow]4.[/yellow] Unpin a market")
    console.print("  [yellow]5.[/yellow] Clear all pins")
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
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pin"])

    elif choice == "2":
        console.print()
        market = Prompt.ask("[cyan]Market to pin[/cyan]")
        if market:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pin", market])

    elif choice == "3":
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pin", "--refresh"])

    elif choice == "4":
        console.print()
        pin_id = Prompt.ask("[cyan]Pin ID to remove[/cyan]")
        if pin_id:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pin", "--unpin", pin_id])

    elif choice == "5":
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pin", "--clear"])
