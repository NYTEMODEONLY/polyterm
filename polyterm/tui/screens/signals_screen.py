"""TUI Screen for Market Signals"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_signals_screen(console: Console):
    """Market signals screen"""
    console.print()
    console.print(Panel("[bold]Market Signals[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Entry/exit signals based on multiple factors[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Analyze specific market")
    console.print("  [yellow]2.[/yellow] Scan for entry signals")
    console.print("  [yellow]3.[/yellow] Scan for exit signals")
    console.print("  [yellow]4.[/yellow] Scan all signals")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        console.print()
        market = Prompt.ask("[cyan]Market to analyze[/cyan]")
        if market:
            subprocess.run(["polyterm", "signals", "--market", market])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "signals", "--scan", "--type", "entry"])

    elif choice == "3":
        console.print()
        subprocess.run(["polyterm", "signals", "--scan", "--type", "exit"])

    elif choice == "4":
        console.print()
        subprocess.run(["polyterm", "signals", "--scan"])
