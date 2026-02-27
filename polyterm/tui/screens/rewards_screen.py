"""Rewards TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_rewards_screen(console: Console):
    """Display rewards estimation screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]Holding & Liquidity Rewards[/bold cyan]\n\n"
        "Estimate your Polymarket holding rewards (4% APY).\n"
        "[dim]Qualifying positions: 20-80 cent range, held 24+ hours.[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - View reward estimates")
    console.print("  [cyan]2[/cyan] - JSON output")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "b"], default="1")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "rewards"]
    elif choice == "2":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "rewards", "--format", "json"]

    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
