"""TUI Screen for Timing Analysis"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_timing_screen(console: Console):
    """Timing analysis screen"""
    console.print()
    console.print(Panel("[bold]Timing Analysis[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Find optimal times to trade[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Enter market to analyze timing[/cyan]")

    if not market:
        return

    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "timing", market])
