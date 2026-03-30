"""Search Screen - Advanced market search with filters"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from ...utils.errors import handle_api_error


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
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "search", "-i"])
    except Exception as e:
        handle_api_error(console, e, "search")
