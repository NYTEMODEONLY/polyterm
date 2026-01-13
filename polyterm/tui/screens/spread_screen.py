"""TUI Screen for Spread Analysis"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_spread_screen(console: Console):
    """Spread analysis screen"""
    console.print()
    console.print(Panel("[bold]Spread Analysis[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Understand bid/ask spread and execution costs[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Enter market to analyze[/cyan]")

    if not market:
        return

    console.print()
    amount = Prompt.ask("[cyan]Trade amount (USD)[/cyan]", default="100")

    console.print()
    subprocess.run(["polyterm", "spread", market, "--amount", amount])
