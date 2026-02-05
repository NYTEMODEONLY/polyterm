"""Watch Screen - Track specific market"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
import subprocess
import sys


def watch_screen(console: RichConsole):
    """Interactive market watch screen
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Watch Specific Market[/bold]", style="cyan"))
    console.print()
    
    console.print("[dim]Search and track a specific market:[/dim]")
    console.print()
    
    # Search for market
    query = console.input("Search for market (or enter Market ID): ").strip()
    
    if not query:
        console.print("[red]No search term provided[/red]")
        return
    
    # Check if it looks like a market ID (hexadecimal)
    is_market_id = all(c in '0123456789abcdefABCDEF-' for c in query)
    
    if is_market_id and len(query) > 20:
        market_id = query
    else:
        console.print(f"\n[yellow]Searching for '{query}'...[/yellow]")
        console.print("[dim]Note: Full market search coming soon. Please use Market ID for now.[/dim]")
        market_id = console.input("\nEnter Market ID: ").strip()
    
    if not market_id:
        console.print("[red]No market ID provided[/red]")
        return
    
    threshold_input = console.input("Alert on probability change > [cyan][default: 5%][/cyan] ").strip() or "5"
    refresh_input = console.input("Check interval in seconds? [cyan][default: 10][/cyan] ").strip() or "10"

    try:
        threshold = str(float(threshold_input))
    except ValueError:
        threshold = "5"
    try:
        refresh = str(int(refresh_input))
    except ValueError:
        refresh = "10"
    
    console.print()
    console.print(f"[green]Watching market {market_id[:8]}...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()
    
    # Build command
    cmd = [
        sys.executable, "-m", "polyterm.cli.main", "watch",
        "--market", market_id,
        "--threshold", threshold,
        "--interval", refresh,
    ]
    
    # Launch watch command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watch stopped[/yellow]")


