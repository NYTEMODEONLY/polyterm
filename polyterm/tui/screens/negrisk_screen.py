"""NegRisk Arbitrage TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_negrisk_screen(console: Console):
    """Display NegRisk arbitrage screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]NegRisk Multi-Outcome Arbitrage[/bold cyan]\n\n"
        "Scan multi-outcome markets for arbitrage opportunities.\n"
        "[dim]When sum of YES prices < $1.00, buying all guarantees profit.[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Scan with default settings")
    console.print("  [cyan]2[/cyan] - Custom minimum spread")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "b"], default="1")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "negrisk"]
    elif choice == "2":
        spread = Prompt.ask("[cyan]Min spread (e.g. 0.03)[/cyan]", default="0.02")
        cmd = [sys.executable, "-m", "polyterm.cli.main", "negrisk", "--min-spread", spread]

    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
