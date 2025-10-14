"""Analytics Screen - Market insights and analysis"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
import subprocess
import sys


def analytics_screen(console: RichConsole):
    """Market analytics and insights
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Market Analytics[/bold]", style="cyan"))
    console.print()
    
    # Submenu for analytics
    console.print("[bold]Select Analytics Type:[/bold]")
    console.print()
    
    menu = Table.grid(padding=(0, 2))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")
    
    menu.add_row("1", "📈 Trending Markets - Most active markets")
    menu.add_row("2", "🔗 Market Correlations - Related markets")
    menu.add_row("3", "🔮 Price Predictions - Trend analysis")
    menu.add_row("4", "📊 Volume Analysis - Volume patterns")
    
    console.print(menu)
    console.print()
    
    choice = console.input("[cyan]Select option (1-4):[/cyan] ").strip()
    console.print()
    
    if choice == '1':
        # Trending Markets
        limit = console.input("How many markets? [cyan][default: 10][/cyan] ").strip() or "10"
        console.print()
        console.print("[green]Fetching trending markets...[/green]")
        console.print()
        
        cmd = [
            sys.executable, "-m", "polyterm.cli.main", "monitor",
            "--limit", limit,
            "--sort", "volume"
        ]
        subprocess.run(cmd)
    
    elif choice == '2':
        # Market Correlations
        console.print("[yellow]Market correlation analysis coming soon![/yellow]")
        console.print("[dim]This feature will show markets that tend to move together.[/dim]")
    
    elif choice == '3':
        # Price Predictions
        console.print("[yellow]Price prediction analysis coming soon![/yellow]")
        console.print("[dim]This feature will analyze price trends and momentum.[/dim]")
    
    elif choice == '4':
        # Volume Analysis
        console.print("[yellow]Volume analysis coming soon![/yellow]")
        console.print("[dim]This feature will identify volume patterns and spikes.[/dim]")
    
    else:
        console.print("[red]Invalid option[/red]")


