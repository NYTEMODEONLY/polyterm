"""TUI Screen for CLOB market price history"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_history_screen(console: Console):
    """CLOB price history screen. Refuses instead of inventing a path."""
    console.print()
    console.print(Panel(
        "[bold]CLOB Price History[/bold]\n"
        "[dim]Uses CLOB GET /prices-history. If that series is missing, "
        "the command refuses instead of inventing a random walk.[/dim]",
        border_style="cyan",
    ))
    console.print()
    console.print("[bold]View real CLOB price history[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Enter market to view history[/cyan]")

    if not market:
        return

    console.print()
    console.print("[cyan]Time Period:[/cyan]")
    console.print("  [yellow]1.[/yellow] Last day")
    console.print("  [yellow]2.[/yellow] Last week")
    console.print("  [yellow]3.[/yellow] Last month")
    console.print("  [yellow]4.[/yellow] All time")
    console.print()

    period_choice = Prompt.ask(
        "[cyan]Select period[/cyan]",
        choices=["1", "2", "3", "4"],
        default="2"
    )

    period_map = {"1": "day", "2": "week", "3": "month", "4": "all"}
    period = period_map.get(period_choice, "week")

    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "history", market, "--period", period, "--chart"])
