"""Quick Trade TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_quicktrade_screen(console: Console):
    """Display quick trade screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]Quick Trade[/bold cyan]\n\n"
        "Analyze trades and get direct Polymarket links.\n"
        "[dim]Prepare your trade, then execute on Polymarket.[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Interactive trade preparation")
    console.print("  [cyan]2[/cyan] - Search for a market")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "b"], default="1")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "quicktrade", "-i"]
    elif choice == "2":
        market = Prompt.ask("[cyan]Search for market[/cyan]")
        if not market:
            return
        side = Prompt.ask("[cyan]Side[/cyan]", choices=["yes", "no"], default="yes")
        amount = Prompt.ask("[cyan]Amount ($)[/cyan]", default="100")
        cmd = [sys.executable, "-m", "polyterm.cli.main", "quicktrade", "-m", market, "-s", side, "-a", amount]

    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
