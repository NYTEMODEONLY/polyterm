"""Search Screen - Advanced market search with filters"""

import subprocess
from rich.console import Console
from rich.panel import Panel


def run_search_screen(console: Console):
    """Launch search command in interactive mode"""
    console.print(Panel(
        "[bold]Market Search[/bold]\n\n"
        "[dim]Find markets with advanced filters for volume, price, liquidity, and more.[/dim]",
        title="[cyan]Search[/cyan]",
        border_style="cyan",
    ))
    console.print()

    try:
        subprocess.run(["polyterm", "search", "-i"])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
