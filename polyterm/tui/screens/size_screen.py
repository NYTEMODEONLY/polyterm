"""Size Screen - Position size calculator"""

import subprocess
from rich.console import Console
from rich.panel import Panel


def run_size_screen(console: Console):
    """Launch size calculator in interactive mode"""
    console.print(Panel(
        "[bold]Position Size Calculator[/bold]\n\n"
        "[dim]Calculate optimal bet sizes using Kelly Criterion.[/dim]\n\n"
        "Enter your bankroll, probability estimate, and market price\n"
        "to get recommended position sizes.",
        title="[cyan]Size[/cyan]",
        border_style="cyan",
    ))
    console.print()

    console.print("[dim]Launching position size calculator...[/dim]")
    console.print()

    try:
        subprocess.run(["polyterm", "size", "-i"])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
