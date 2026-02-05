"""Chart Screen - View price history charts"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_chart_screen(console: Console):
    """Launch chart command"""
    console.print(Panel(
        "[bold]Price History Charts[/bold]\n\n"
        "[dim]View ASCII price charts for any market.[/dim]\n\n"
        "Shows price movement over time with customizable timeframes.",
        title="[cyan]Chart[/cyan]",
        border_style="cyan",
    ))
    console.print()

    market = Prompt.ask(
        "[cyan]Enter market ID or search term[/cyan]",
        default=""
    )

    if not market:
        console.print("[yellow]No market specified.[/yellow]")
        return

    hours = Prompt.ask(
        "[cyan]Hours of history[/cyan]",
        default="24"
    )

    view_type = Prompt.ask(
        "[cyan]View type[/cyan]",
        choices=["chart", "sparkline"],
        default="chart"
    )

    console.print()
    console.print("[dim]Generating chart...[/dim]")
    console.print()

    # Build command
    cmd = [sys.executable, "-m", "polyterm.cli.main", "chart", "-m", market, "-h", hours]
    if view_type == "sparkline":
        cmd.append("--sparkline")

    try:
        subprocess.run(cmd)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
