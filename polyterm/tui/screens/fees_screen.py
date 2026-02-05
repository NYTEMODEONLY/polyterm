"""Fees Screen - Calculate trading fees and slippage"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel


def run_fees_screen(console: Console):
    """Launch fees calculator in interactive mode"""
    console.print(Panel(
        "[bold]Fee & Slippage Calculator[/bold]\n\n"
        "[dim]Calculate the true cost of your trades including fees and slippage.[/dim]",
        title="[cyan]Fees[/cyan]",
        border_style="cyan",
    ))
    console.print()

    try:
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "fees", "-i"])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
