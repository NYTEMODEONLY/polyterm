"""Calendar Screen - View upcoming market resolutions"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_calendar_screen(console: Console):
    """Launch calendar command"""
    console.print(Panel(
        "[bold]Market Calendar[/bold]\n\n"
        "[dim]View markets ending soon to plan your trades.[/dim]",
        title="[cyan]Calendar[/cyan]",
        border_style="cyan",
    ))
    console.print()

    days = Prompt.ask(
        "[cyan]Days to look ahead[/cyan]",
        default="7"
    )

    console.print()
    console.print("[dim]Fetching upcoming resolutions...[/dim]")
    console.print()

    try:
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "calendar", "--days", days])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
