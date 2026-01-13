"""Simulate Screen - Position P&L calculator"""

import subprocess
import sys
from rich.console import Console as RichConsole
from rich.panel import Panel


def simulate_screen(console: RichConsole):
    """Launch position simulator in interactive mode

    Args:
        console: Rich Console instance
    """
    console.print(Panel(
        "[bold]Position Simulator[/bold]\n"
        "[dim]Calculate potential profit/loss before trading[/dim]",
        style="cyan"
    ))
    console.print()

    console.print("[cyan]This tool helps you understand:[/cyan]")
    console.print("  - How much you could win or lose")
    console.print("  - Your potential ROI")
    console.print("  - What happens at different exit prices")
    console.print("  - Fees and their impact")
    console.print()

    console.print("[dim]Starting interactive simulator...[/dim]")
    console.print()

    # Run the simulate command in interactive mode
    try:
        subprocess.run([sys.executable, "-m", "polyterm", "simulate", "-i"])
    except Exception as e:
        console.print(f"[red]Error running simulator: {e}[/red]")
        console.print("[dim]Try running: polyterm simulate -i[/dim]")
