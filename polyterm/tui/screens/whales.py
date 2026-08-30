"""Whales Screen - high-volume market heuristic (not whale identity)"""

from rich.panel import Panel
from rich.console import Console as RichConsole
import subprocess
import sys


def whales_screen(console: RichConsole):
    """Interactive high-volume market screen.

    This path lists Gamma 24h volume. It does not identify traders.
    Wallet-level whale trades are available via `polyterm whales --wallets`.
    """
    console.print(Panel(
        "[bold]High-Volume Market Tracker[/bold]\n"
        "[dim]Gamma 24h volume heuristic — not whale wallets or trade identity. "
        "For wallet-level trades run polyterm whales --wallets.[/dim]",
        style="cyan",
    ))
    console.print()

    console.print("[dim]Configure volume heuristic parameters:[/dim]")
    console.print()

    min_amount = console.input("Minimum 24hr volume? [cyan][default: $10,000][/cyan] $").strip() or "10000"
    hours = console.input("Lookback period in hours? [cyan][default: 24][/cyan] ").strip() or "24"
    limit = console.input("Maximum results to show? [cyan][default: 20][/cyan] ").strip() or "20"

    console.print()
    console.print("[green]Listing high-volume markets...[/green]")
    console.print()

    cmd = [
        sys.executable, "-m", "polyterm.cli.main", "whales",
        "--volume",
        "--min-amount", min_amount,
        "--hours", hours,
        "--limit", limit,
    ]

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]High-volume listing stopped[/yellow]")
