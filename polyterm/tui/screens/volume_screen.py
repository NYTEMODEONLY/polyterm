"""TUI Screen for Volume Profile Analysis"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_volume_screen(console: Console):
    """Volume profile analysis screen"""
    console.print()
    console.print(Panel("[bold]Volume Profile Analysis[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Analyze volume distribution at different price levels[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Enter market name[/cyan]")

    if not market:
        return

    levels = Prompt.ask("[cyan]Number of price levels[/cyan]", default="10")

    console.print()
    subprocess.run(["polyterm", "volume", "-m", market, "-l", levels])
