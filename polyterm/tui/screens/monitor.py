"""Monitor Screen - Real-time market tracking"""

from rich.panel import Panel
from rich.console import Console as RichConsole
import subprocess
import sys


def monitor_screen(console: RichConsole):
    """Interactive monitor screen with guided setup
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Real-Time Market Monitor[/bold]", style="cyan"))
    console.print()
    
    # Get parameters interactively
    console.print("[dim]Configure your market monitor:[/dim]")
    console.print()
    
    limit = console.input("How many markets to display? [cyan][default: 10][/cyan] ").strip() or "10"
    category = console.input("Category filter (or press Enter for all): [dim]politics/crypto/sports[/dim] ").strip() or None
    refresh = console.input("Refresh rate in seconds? [cyan][default: 2][/cyan] ").strip() or "2"
    active_only = console.input("Active markets only? [cyan][Y/n][/cyan] ").strip().lower() != 'n'
    
    console.print()
    console.print("[green]Starting monitor...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()
    
    # Build command
    cmd = [
        sys.executable, "-m", "polyterm.cli.main", "monitor",
        "--limit", limit,
        "--refresh", refresh,
    ]
    
    if category:
        cmd.extend(["--category", category])
    
    if active_only:
        cmd.append("--active-only")
    
    # Launch monitor command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")


