"""TUI Screen for Market Correlation Finder"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_correlate_screen(console: Console):
    """Market correlation finder screen"""
    console.print()
    console.print(Panel("[bold]Market Correlation Finder[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Find related markets for hedging or doubling exposure[/bold]")
    console.print()
    console.print("[dim]Discovers positively correlated, inversely correlated,[/dim]")
    console.print("[dim]and time-variant markets based on your selection.[/dim]")
    console.print()

    search = Prompt.ask("[cyan]Search for market[/cyan]", default="")

    if search:
        limit = Prompt.ask("[cyan]Number of results[/cyan]", default="10")
        console.print()
        try:
            subprocess.run(["polyterm", "correlate", "--market", search, "--limit", limit])
        except Exception:
            subprocess.run(["polyterm", "correlate", "--market", search])
