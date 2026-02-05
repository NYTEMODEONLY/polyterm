"""TUI Screen for Liquidity Depth Analyzer"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_depth_screen(console: Console):
    """Liquidity depth analyzer screen"""
    console.print()
    console.print(Panel("[bold]Liquidity Depth Analyzer[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Analyze order book depth and estimate slippage[/bold]")
    console.print()
    console.print("[dim]See liquidity at each price level and how much[/dim]")
    console.print("[dim]slippage to expect for different trade sizes.[/dim]")
    console.print()

    search = Prompt.ask("[cyan]Search for market[/cyan]", default="")

    if search:
        size = Prompt.ask("[cyan]Trade size to analyze ($)[/cyan]", default="1000")
        console.print()
        try:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "depth", "--market", search, "--size", size])
        except Exception:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "depth", "--market", search])
