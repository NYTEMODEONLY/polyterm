"""Arbitrage Screen - Scan for arbitrage opportunities"""

import subprocess
import sys
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table


def arbitrage_screen(console: RichConsole):
    """Scan for arbitrage opportunities across markets

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Arbitrage Scanner[/bold]", style="cyan"))
    console.print()

    # Settings submenu
    console.print("[bold]Scan Settings:[/bold]")
    console.print()

    # Get minimum spread
    min_spread = console.input(
        "Minimum spread % [cyan][default: 2.5][/cyan] "
    ).strip() or "2.5"
    try:
        min_spread = float(min_spread) / 100
        if min_spread < 0.001:
            min_spread = 0.025
    except ValueError:
        min_spread = 0.025

    # Get limit
    limit = console.input(
        "Max opportunities to show [cyan][default: 10][/cyan] "
    ).strip() or "10"
    try:
        limit = int(limit)
        if limit < 1:
            limit = 10
        elif limit > 50:
            limit = 50
    except ValueError:
        limit = 10

    # Include Kalshi
    include_kalshi = console.input(
        "Include Kalshi cross-platform? [cyan](y/n)[/cyan] [default: n] "
    ).strip().lower()
    include_kalshi = include_kalshi == 'y'

    console.print()
    console.print("[green]Scanning for arbitrage opportunities...[/green]")
    console.print()

    # Build and run command
    cmd = [sys.executable, "-m", "polyterm.cli.main", "arbitrage", f"--min-spread={min_spread}", f"--limit={limit}"]
    if include_kalshi:
        cmd.append("--include-kalshi")

    try:
        result = subprocess.run(cmd, capture_output=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Scan cancelled.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
