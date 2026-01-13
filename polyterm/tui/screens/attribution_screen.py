"""TUI Screen for Performance Attribution"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_attribution_screen(console: Console):
    """Performance attribution screen"""
    console.print()
    console.print(Panel("[bold]Performance Attribution[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Analyze what's driving your trading performance[/bold]")
    console.print()
    console.print("[cyan]Time Period:[/cyan]")
    console.print("  [yellow]1.[/yellow] Last week")
    console.print("  [yellow]2.[/yellow] Last month")
    console.print("  [yellow]3.[/yellow] Last quarter")
    console.print("  [yellow]4.[/yellow] Last year")
    console.print("  [yellow]5.[/yellow] All time")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select period[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="2"
    )

    if choice == "b":
        return

    period_map = {
        "1": "week",
        "2": "month",
        "3": "quarter",
        "4": "year",
        "5": "all",
    }

    period = period_map.get(choice, "month")
    console.print()
    subprocess.run(["polyterm", "attribution", "--period", period])
