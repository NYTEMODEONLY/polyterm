"""15-Minute Crypto Markets TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_crypto15m_screen(console: Console):
    """Display 15-minute crypto markets screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]15-Minute Crypto Markets[/bold cyan]\n\n"
        "Trade short-term crypto price predictions.\n"
        "Markets resolve every 15 minutes using Chainlink oracles.\n\n"
        "[dim]Supported: BTC, ETH, SOL, XRP[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Monitor all 15M markets")
    console.print("  [cyan]2[/cyan] - Monitor Bitcoin (BTC) only")
    console.print("  [cyan]3[/cyan] - Monitor Ethereum (ETH) only")
    console.print("  [cyan]4[/cyan] - Monitor Solana (SOL) only")
    console.print("  [cyan]5[/cyan] - Monitor XRP only")
    console.print("  [cyan]6[/cyan] - Interactive mode (analyze & trade)")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "4", "5", "6", "b"], default="1")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "crypto15m"]
    elif choice == "2":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "crypto15m", "-c", "BTC"]
    elif choice == "3":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "crypto15m", "-c", "ETH"]
    elif choice == "4":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "crypto15m", "-c", "SOL"]
    elif choice == "5":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "crypto15m", "-c", "XRP"]
    elif choice == "6":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "crypto15m", "-i"]

    console.print()
    console.print("[dim]Launching 15M crypto monitor...[/dim]")
    console.print("[dim]Press Ctrl+C to exit and return to menu[/dim]")
    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
