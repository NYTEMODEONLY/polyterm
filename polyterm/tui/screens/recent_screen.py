"""Recent Screen - View recently viewed markets"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel


def run_recent_screen(console: Console):
    """Launch recent markets view"""
    console.print(Panel(
        "[bold]Recently Viewed Markets[/bold]\n\n"
        "[dim]See markets you've recently interacted with.[/dim]\n\n"
        "Quickly return to markets you were researching.",
        title="[cyan]Recent[/cyan]",
        border_style="cyan",
    ))
    console.print()

    try:
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "recent"])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
