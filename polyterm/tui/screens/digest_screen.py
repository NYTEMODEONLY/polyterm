"""TUI Screen for Digest Summary"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_digest_screen(console: Console):
    """Digest summary screen"""
    console.print()
    console.print(Panel("[bold]Digest[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Get a summary of trading and market activity[/bold]")
    console.print()
    console.print("[cyan]Time Period:[/cyan]")
    console.print("  [yellow]1.[/yellow] Today")
    console.print("  [yellow]2.[/yellow] Yesterday")
    console.print("  [yellow]3.[/yellow] This week")
    console.print("  [yellow]4.[/yellow] This month")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select period[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="1"
    )

    if choice == "b":
        return

    period_map = {
        "1": "today",
        "2": "yesterday",
        "3": "week",
        "4": "month",
    }

    period = period_map.get(choice, "today")
    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "digest", "--period", period])
