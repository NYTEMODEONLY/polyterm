"""Main Menu for PolyTerm TUI"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class MainMenu:
    """Main menu display and input handler"""
    
    def __init__(self):
        self.console = Console()
    
    def display(self):
        """Display main menu with all options"""
        menu = Table.grid(padding=(0, 2))
        menu.add_column(style="cyan bold", justify="right", width=3)
        menu.add_column(style="white")
        
        menu.add_row("1", "📊 Monitor Markets - Real-time market tracking")
        menu.add_row("2", "🐋 Whale Activity - High-volume markets")
        menu.add_row("3", "👁  Watch Market - Track specific market")
        menu.add_row("4", "📈 Market Analytics - Trends and predictions")
        menu.add_row("5", "💼 Portfolio - View your positions")
        menu.add_row("6", "📤 Export Data - Export to JSON/CSV")
        menu.add_row("7", "⚙️  Settings - Configuration")
        menu.add_row("", "")
        menu.add_row("h", "❓ Help - View documentation")
        menu.add_row("q", "🚪 Quit - Exit PolyTerm")
        
        panel = Panel(
            menu,
            title="[bold yellow]Main Menu[/bold yellow]",
            border_style="green",
            padding=(1, 2)
        )
        
        self.console.print(panel)
        self.console.print()
    
    def get_choice(self) -> str:
        """Get user menu choice
        
        Returns:
            User's choice as lowercase string
        """
        return self.console.input("[bold cyan]Select an option:[/bold cyan] ").strip().lower()


