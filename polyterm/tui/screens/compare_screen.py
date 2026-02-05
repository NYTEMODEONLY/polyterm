"""Compare Screen - Compare markets side by side"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel


def run_compare_screen(console: Console):
    """Launch compare command in interactive mode"""
    console.print(Panel(
        "[bold]Market Comparison[/bold]\n\n"
        "[dim]Compare multiple markets side by side.[/dim]\n\n"
        "See price trends, volumes, and key metrics together.",
        title="[cyan]Compare[/cyan]",
        border_style="cyan",
    ))
    console.print()

    console.print("[dim]Launching interactive comparison...[/dim]")
    console.print()

    try:
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "compare", "-i"])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
