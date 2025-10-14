"""Main Menu for PolyTerm TUI"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel


class MainMenu:
    """Main menu display and input handler"""
    
    def __init__(self):
        self.console = Console()
    
    def display(self):
        """Display main menu with all options, responsive to terminal width"""
        # Get terminal width, fallback to 80 if not available
        try:
            width = self.console.size.width
        except:
            width = 80
        
        # Force narrow terminal for testing if COLUMNS env var is set
        import os
        if 'COLUMNS' in os.environ:
            width = int(os.environ['COLUMNS'])
        
        # Adjust menu content based on terminal width
        if width >= 80:
            # Full descriptions for wide terminals
            menu_items = [
                ("1", "📊 Monitor Markets - Real-time market tracking"),
                ("2", "🐋 Whale Activity - High-volume markets"),
                ("3", "👁  Watch Market - Track specific market"),
                ("4", "📈 Market Analytics - Trends and predictions"),
                ("5", "💼 Portfolio - View your positions"),
                ("6", "📤 Export Data - Export to JSON/CSV"),
                ("7", "⚙️  Settings - Configuration"),
                ("", ""),
                ("h", "❓ Help - View documentation"),
                ("q", "🚪 Quit - Exit PolyTerm")
            ]
        elif width >= 60:
            # Medium descriptions for medium terminals
            menu_items = [
                ("1", "📊 Monitor Markets"),
                ("2", "🐋 Whale Activity"),
                ("3", "👁  Watch Market"),
                ("4", "📈 Market Analytics"),
                ("5", "💼 Portfolio"),
                ("6", "📤 Export Data"),
                ("7", "⚙️  Settings"),
                ("", ""),
                ("h", "❓ Help"),
                ("q", "🚪 Quit")
            ]
        else:
            # Compact menu for narrow terminals
            menu_items = [
                ("1", "📊 Monitor"),
                ("2", "🐋 Whales"),
                ("3", "👁  Watch"),
                ("4", "📈 Analytics"),
                ("5", "💼 Portfolio"),
                ("6", "📤 Export"),
                ("7", "⚙️  Settings"),
                ("", ""),
                ("h", "❓ Help"),
                ("q", "🚪 Quit")
            ]
        
        menu = Table.grid(padding=(0, 1))
        menu.add_column(style="cyan bold", justify="right", width=3)
        menu.add_column(style="white")
        
        for key, desc in menu_items:
            menu.add_row(key, desc)
        
        # Adjust panel width based on terminal width
        panel_width = min(width - 4, 70) if width >= 60 else width - 2
        
        panel = Panel(
            menu,
            title="[bold yellow]Main Menu[/bold yellow]",
            border_style="green",
            padding=(1, 1),
            width=panel_width
        )
        
        self.console.print(panel)
        self.console.print()
    
    def get_choice(self) -> str:
        """Get user menu choice
        
        Returns:
            User's choice as lowercase string
        """
        return self.console.input("[bold cyan]Select an option:[/bold cyan] ").strip().lower()


