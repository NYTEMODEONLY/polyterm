"""Whales Screen - High-volume market tracking"""

from rich.panel import Panel
from rich.console import Console as RichConsole
import subprocess
import sys


def whales_screen(console: RichConsole):
    """Interactive whale tracking screen
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]High-Volume Market Tracker[/bold]", style="cyan"))
    console.print()
    
    console.print("[dim]Configure whale detection parameters:[/dim]")
    console.print()
    
    min_amount = console.input("Minimum 24hr volume? [cyan][default: $10,000][/cyan] $").strip() or "10000"
    hours = console.input("Lookback period in hours? [cyan][default: 24][/cyan] ").strip() or "24"
    limit = console.input("Maximum results to show? [cyan][default: 20][/cyan] ").strip() or "20"
    
    console.print()
    console.print("[green]Tracking whale activity...[/green]")
    console.print()
    
    # Build command
    cmd = [
        sys.executable, "-m", "polyterm.cli.main", "whales",
        "--min-amount", min_amount,
        "--hours", hours,
        "--limit", limit,
    ]
    
    # Launch whales command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Whale tracking stopped[/yellow]")


