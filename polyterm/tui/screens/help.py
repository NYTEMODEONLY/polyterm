"""Help Screen - Documentation and guides"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
from rich.markdown import Markdown


def help_screen(console: RichConsole):
    """Help and documentation
    
    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Help & Documentation[/bold]", style="cyan"))
    console.print()
    
    # Keyboard Shortcuts
    console.print("[bold yellow]Keyboard Shortcuts:[/bold yellow]")
    console.print()
    
    shortcuts = Table(show_header=False, box=None, padding=(0, 1))
    shortcuts.add_column(style="cyan bold", width=8)
    shortcuts.add_column(style="white")
    
    shortcuts.add_row("1-7", "Navigate to menu option")
    shortcuts.add_row("h, ?", "Show this help screen")
    shortcuts.add_row("q", "Quit / Return to menu")
    shortcuts.add_row("Ctrl+C", "Stop current operation")
    
    console.print(shortcuts)
    console.print()
    
    # Features
    console.print("[bold yellow]Features:[/bold yellow]")
    console.print()
    
    features = Table(show_header=False, box=None, padding=(0, 1))
    features.add_column(style="cyan bold", width=2)
    features.add_column(style="white")
    
    features.add_row("📊", "[bold]Monitor:[/bold] Real-time market tracking with customizable refresh rates")
    features.add_row("🐋", "[bold]Whales:[/bold] High-volume market detection and tracking")
    features.add_row("👁", "[bold]Watch:[/bold] Track specific markets with price alerts")
    features.add_row("📈", "[bold]Analytics:[/bold] Market trends, correlations, and predictions")
    features.add_row("💼", "[bold]Portfolio:[/bold] Track your positions and P&L")
    features.add_row("📤", "[bold]Export:[/bold] Export market data to JSON/CSV")
    features.add_row("⚙️", "[bold]Settings:[/bold] Configure alerts, API, and display options")
    
    console.print(features)
    console.print()
    
    # CLI Commands
    console.print("[bold yellow]CLI Commands (for power users):[/bold yellow]")
    console.print()
    console.print("You can also use direct CLI commands:")
    console.print()
    console.print("[dim]  polyterm monitor --limit 10[/dim]")
    console.print("[dim]  polyterm whales --hours 24[/dim]")
    console.print("[dim]  polyterm watch <market-id>[/dim]")
    console.print("[dim]  polyterm export --market <id> --format json[/dim]")
    console.print("[dim]  polyterm portfolio --wallet <address>[/dim]")
    console.print()
    
    # API Status
    console.print("[bold yellow]API Status:[/bold yellow]")
    console.print()
    console.print("✅ [green]Gamma API[/green] - Live market data")
    console.print("✅ [green]CLOB API[/green] - Order book data")
    console.print("⚠️  [yellow]Subgraph API[/yellow] - Limited (deprecated by PolyMarket)")
    console.print()
    
    # Links
    console.print("[bold yellow]Resources:[/bold yellow]")
    console.print()
    console.print("📖 [link=https://github.com/NYTEMODEONLY/polyterm]GitHub Repository[/link]")
    console.print("📄 [link=https://docs.polymarket.com]PolyMarket Docs[/link]")
    console.print("🐛 [link=https://github.com/NYTEMODEONLY/polyterm/issues]Report Issues[/link]")
    console.print()


