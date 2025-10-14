"""Portfolio Screen - User position tracking"""

from rich.panel import Panel
from rich.console import Console as RichConsole
import subprocess
import sys


def portfolio_screen(console: RichConsole):
    """Portfolio management screen
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Portfolio Manager[/bold]", style="cyan"))
    console.print()
    
    console.print("[dim]View your PolyMarket positions:[/dim]")
    console.print()
    
    wallet = console.input("Wallet address (or press Enter for config): ").strip()
    
    if not wallet:
        console.print("[yellow]Using wallet from config file...[/yellow]")
    
    console.print()
    console.print("[green]Loading portfolio...[/green]")
    console.print()
    
    # Build command
    cmd = [sys.executable, "-m", "polyterm.cli.main", "portfolio"]
    
    if wallet:
        cmd.extend(["--wallet", wallet])
    
    # Launch portfolio command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Portfolio view stopped[/yellow]")


