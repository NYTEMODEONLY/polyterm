"""TUI Screen for DEMO strategy simulation (not historical backtesting)"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_backtest_screen(console: Console):
    """DEMO strategy simulation screen. Does not replay historical data."""
    console.print()
    console.print(Panel(
        "[bold yellow]DEMO Strategy Simulator[/bold yellow]\n"
        "[dim]This does not replay historical Polymarket trades or prices. "
        "Results are seeded random numbers.[/dim]",
        border_style="yellow",
    ))
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Interactive DEMO")
    console.print("  [yellow]2.[/yellow] Quick DEMO - Momentum")
    console.print("  [yellow]3.[/yellow] Quick DEMO - Mean Reversion")
    console.print("  [yellow]4.[/yellow] Quick DEMO - Whale Follow")
    console.print("  [yellow]5.[/yellow] Quick DEMO - Contrarian")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "1":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "backtest", "--demo", "-i"])
    elif choice == "2":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "backtest", "--demo", "-s", "momentum", "-p", "30d"])
    elif choice == "3":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "backtest", "--demo", "-s", "mean-reversion", "-p", "30d"])
    elif choice == "4":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "backtest", "--demo", "-s", "whale-follow", "-p", "30d"])
    elif choice == "5":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "backtest", "--demo", "-s", "contrarian", "-p", "30d"])
