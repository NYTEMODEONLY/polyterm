"""TUI Controller - Main application loop"""

from rich.console import Console
from .logo import display_logo
from .menu import MainMenu
from .screens import (
    monitor_screen,
    whales_screen,
    watch_screen,
    analytics_screen,
    portfolio_screen,
    export_screen,
    settings_screen,
    help_screen,
)


class TUIController:
    """Main TUI controller and event loop"""
    
    def __init__(self):
        self.console = Console()
        self.menu = MainMenu()
        self.running = True
    
    def run(self):
        """Main TUI loop - display menu and handle user input"""
        try:
            self.console.clear()
            display_logo(self.console)
            
            while self.running:
                self.menu.display()
                choice = self.menu.get_choice()
                
                # Handle menu choices
                if choice == '1' or choice == 'm':
                    monitor_screen(self.console)
                elif choice == '2' or choice == 'w':
                    whales_screen(self.console)
                elif choice == '3':
                    watch_screen(self.console)
                elif choice == '4' or choice == 'a':
                    analytics_screen(self.console)
                elif choice == '5' or choice == 'p':
                    portfolio_screen(self.console)
                elif choice == '6' or choice == 'e':
                    export_screen(self.console)
                elif choice == '7' or choice == 's':
                    settings_screen(self.console)
                elif choice == 'h' or choice == '?':
                    help_screen(self.console)
                elif choice == 'q' or choice == 'quit' or choice == 'exit':
                    self.quit()
                else:
                    self.console.print("[red]Invalid choice. Try again.[/red]")
                
                # Return to menu (unless quitting)
                if self.running and choice != 'q' and choice != 'quit' and choice != 'exit':
                    input("\nPress Enter to return to menu...")
                    self.console.clear()
                    display_logo(self.console)
        
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.console.print("\n\n[yellow]Interrupted. Exiting...[/yellow]")
            self.running = False
    
    def quit(self):
        """Exit TUI with farewell message"""
        self.console.print("\n[yellow]Thanks for using PolyTerm! 📊[/yellow]")
        self.console.print("[dim]Happy trading![/dim]\n")
        self.running = False


