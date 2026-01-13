"""Stats Screen - View detailed market statistics"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_stats_screen(console: Console):
    """Launch stats command"""
    console.print(Panel(
        "[bold]Market Statistics[/bold]\n\n"
        "[dim]View volatility, trends, RSI, and other technical indicators.[/dim]",
        title="[cyan]Stats[/cyan]",
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

    console.print()
    console.print("[dim]Analyzing market...[/dim]")
    console.print()

    try:
        subprocess.run(["polyterm", "stats", "-m", market])
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
