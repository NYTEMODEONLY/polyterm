"""TUI Screen for Quick Trade Calculator"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_trade_screen(console: Console):
    """Quick trade calculator screen"""
    console.print()
    console.print(Panel("[bold]Quick Trade Calculator[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Analyze everything before you trade[/bold]")
    console.print()
    console.print("[dim]Shows fees, slippage, breakeven, profit scenarios,[/dim]")
    console.print("[dim]and risk/reward for any potential trade.[/dim]")
    console.print()

    search = Prompt.ask("[cyan]Search for market[/cyan]", default="")

    if search:
        side = Prompt.ask("[cyan]Side[/cyan]", choices=["yes", "no"], default="yes")
        amount = Prompt.ask("[cyan]Trade amount ($)[/cyan]", default="100")
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "trade", "--market", search, "--side", side, "--amount", amount])
