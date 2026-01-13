"""TUI Screen for Strategy Backtesting"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_backtest_screen(console: Console):
    """Strategy backtesting screen"""
    console.print()
    console.print(Panel("[bold]Strategy Backtester[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Test trading strategies on historical data[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Interactive mode (recommended)")
    console.print("  [yellow]2.[/yellow] Quick test - Momentum strategy")
    console.print("  [yellow]3.[/yellow] Quick test - Mean Reversion strategy")
    console.print("  [yellow]4.[/yellow] Quick test - Whale Follow strategy")
    console.print("  [yellow]5.[/yellow] Quick test - Contrarian strategy")
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
        subprocess.run(["polyterm", "backtest", "-i"])
    elif choice == "2":
        subprocess.run(["polyterm", "backtest", "-s", "momentum", "-p", "30d"])
    elif choice == "3":
        subprocess.run(["polyterm", "backtest", "-s", "mean-reversion", "-p", "30d"])
    elif choice == "4":
        subprocess.run(["polyterm", "backtest", "-s", "whale-follow", "-p", "30d"])
    elif choice == "5":
        subprocess.run(["polyterm", "backtest", "-s", "contrarian", "-p", "30d"])
