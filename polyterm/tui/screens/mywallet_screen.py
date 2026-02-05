"""My Wallet TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_mywallet_screen(console: Console):
    """Display wallet management screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]My Wallet[/bold cyan]\n\n"
        "Connect and track your Polymarket activity.\n"
        "[dim]VIEW-ONLY - no private keys required[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Connect/change wallet")
    console.print("  [cyan]2[/cyan] - View wallet summary")
    console.print("  [cyan]3[/cyan] - View positions")
    console.print("  [cyan]4[/cyan] - View trade history")
    console.print("  [cyan]5[/cyan] - View P&L summary")
    console.print("  [cyan]6[/cyan] - Interactive mode")
    console.print("  [cyan]7[/cyan] - Disconnect wallet")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "4", "5", "6", "7", "b"], default="2")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet", "--connect"]
    elif choice == "2":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet"]
    elif choice == "3":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet", "-p"]
    elif choice == "4":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet", "-h"]
    elif choice == "5":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet", "--pnl"]
    elif choice == "6":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet", "-i"]
    elif choice == "7":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "mywallet", "--disconnect"]

    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
