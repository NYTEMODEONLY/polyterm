"""TUI Screen for Watchdog Monitoring"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_watchdog_screen(console: Console):
    """Watchdog monitoring screen"""
    console.print()
    console.print(Panel("[bold]Watchdog Monitor[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Continuous monitoring with custom conditions[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Market to watch[/cyan]")

    if not market:
        return

    console.print()
    console.print("[cyan]Alert condition:[/cyan]")
    console.print("  [yellow]1.[/yellow] Price goes above threshold")
    console.print("  [yellow]2.[/yellow] Price goes below threshold")
    console.print("  [yellow]3.[/yellow] Price changes by amount")
    console.print("  [yellow]4.[/yellow] Any significant change (default)")
    console.print()

    cond_choice = Prompt.ask(
        "[cyan]Select condition[/cyan]",
        choices=["1", "2", "3", "4"],
        default="4"
    )

    args = [sys.executable, "-m", "polyterm.cli.main", "watchdog", "-m", market]

    if cond_choice == "1":
        threshold = Prompt.ask("[cyan]Alert when above (e.g., 0.70)[/cyan]")
        args.extend(["--above", threshold])

    elif cond_choice == "2":
        threshold = Prompt.ask("[cyan]Alert when below (e.g., 0.40)[/cyan]")
        args.extend(["--below", threshold])

    elif cond_choice == "3":
        change = Prompt.ask("[cyan]Alert on change (e.g., 0.05 for 5%)[/cyan]", default="0.05")
        args.extend(["--change", change])

    console.print()
    console.print("[dim]Press Ctrl+C to stop monitoring[/dim]")
    console.print()

    subprocess.run(args)
