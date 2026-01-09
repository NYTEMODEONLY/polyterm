"""Main Menu for PolyTerm TUI"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import polyterm
import requests
import re
from packaging import version


class MainMenu:
    """Main menu display and input handler"""
    
    def __init__(self):
        self.console = Console()
    
    def check_for_updates(self) -> tuple[str, str]:
        """Check if there's a newer version available on PyPI
        
        Returns:
            Tuple of (update_indicator_string, latest_version)
        """
        try:
            # Get current version - force fresh import to avoid caching issues
            import importlib
            importlib.reload(polyterm)
            current_version = polyterm.__version__
            
            # Get latest version from PyPI
            response = requests.get("https://pypi.org/pypi/polyterm/json", timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_version = data["info"]["version"]
                
                # Compare versions
                if version.parse(latest_version) > version.parse(current_version):
                    return f" [bold green]🔄 Update Available: v{latest_version}[/bold green]", latest_version
            
        except Exception:
            # If update check fails, silently continue
            pass
        
        return "", ""
    
    def quick_update(self) -> bool:
        """Perform a quick update from the main menu
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            import subprocess
            import sys
            import importlib
            
            self.console.print("\n[bold green]🔄 Quick Update Starting...[/bold green]")
            
            # Check for pipx first (preferred)
            try:
                subprocess.run(["pipx", "--version"], capture_output=True, check=True)
                update_cmd = ["pipx", "upgrade", "polyterm"]
                method = "pipx"
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback to pip
                update_cmd = [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"]
                method = "pip"
            
            self.console.print(f"[dim]Using {method} to update...[/dim]")
            
            # Run update
            result = subprocess.run(update_cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                # Force reload to get new version
                importlib.reload(polyterm)
                new_version = polyterm.__version__
                
                self.console.print(f"[bold green]✅ Update successful![/bold green]")
                self.console.print(f"[green]Updated to version {new_version}[/green]")
                self.console.print()
                self.console.print("[bold yellow]🔄 Restart Required[/bold yellow]")
                self.console.print("[yellow]Please restart PolyTerm to use the new version.[/yellow]")
                return True
            else:
                self.console.print("[bold red]❌ Update failed[/bold red]")
                if result.stderr:
                    self.console.print(f"[red]Error: {result.stderr}[/red]")
                return False
                
        except Exception as e:
            self.console.print(f"[bold red]❌ Update error: {e}[/bold red]")
            return False
    
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
        
        # Check for updates first
        update_indicator, latest_version = self.check_for_updates()
        has_update = bool(latest_version)
        
        # Adjust menu content based on terminal width
        if width >= 80:
            # Full descriptions for wide terminals
            menu_items = [
                ("1", "📊 Monitor Markets - Real-time market tracking"),
                ("2", "🔴 Live Monitor - Dedicated terminal window"),
                ("3", "🐋 Whale Activity - High-volume markets"),
                ("4", "👁  Watch Market - Track specific market"),
                ("5", "📈 Market Analytics - Trends and predictions"),
                ("6", "💼 Portfolio - View your positions"),
                ("7", "📤 Export Data - Export to JSON/CSV"),
                ("8", "⚙️  Settings - Configuration"),
                ("", ""),
                ("9", "💰 Arbitrage - Scan for arbitrage opportunities"),
                ("10", "📈 Predictions - Signal-based analysis"),
                ("11", "👛 Wallets - Smart money tracking"),
                ("12", "🔔 Alerts - Manage notifications"),
                ("13", "📖 Order Book - Analyze market depth"),
                ("", ""),
                ("h", "❓ Help - View documentation"),
                ("q", "🚪 Quit - Exit PolyTerm")
            ]

            # Add quick update option if update is available
            if has_update:
                menu_items.insert(-2, ("u", f"🔄 Quick Update to v{latest_version}"))
        elif width >= 60:
            # Medium descriptions for medium terminals
            menu_items = [
                ("1", "📊 Monitor Markets"),
                ("2", "🔴 Live Monitor"),
                ("3", "🐋 Whale Activity"),
                ("4", "👁  Watch Market"),
                ("5", "📈 Market Analytics"),
                ("6", "💼 Portfolio"),
                ("7", "📤 Export Data"),
                ("8", "⚙️  Settings"),
                ("", ""),
                ("9", "💰 Arbitrage"),
                ("10", "📈 Predictions"),
                ("11", "👛 Wallets"),
                ("12", "🔔 Alerts"),
                ("13", "📖 Order Book"),
                ("", ""),
                ("h", "❓ Help"),
                ("q", "🚪 Quit")
            ]

            # Add quick update option if update is available
            if has_update:
                menu_items.insert(-2, ("u", f"🔄 Update to v{latest_version}"))
        else:
            # Compact menu for narrow terminals
            menu_items = [
                ("1", "📊 Monitor"),
                ("2", "🔴 Live"),
                ("3", "🐋 Whales"),
                ("4", "👁  Watch"),
                ("5", "📈 Analytics"),
                ("6", "💼 Portfolio"),
                ("7", "📤 Export"),
                ("8", "⚙️  Settings"),
                ("", ""),
                ("9", "💰 Arbitrage"),
                ("10", "📈 Predict"),
                ("11", "👛 Wallets"),
                ("12", "🔔 Alerts"),
                ("13", "📖 Book"),
                ("", ""),
                ("h", "❓ Help"),
                ("q", "🚪 Quit")
            ]

            # Add quick update option if update is available
            if has_update:
                menu_items.insert(-2, ("u", f"🔄 Update"))
        
        menu = Table.grid(padding=(0, 1))
        menu.add_column(style="cyan bold", justify="right", width=3)
        menu.add_column(style="white")
        
        for key, desc in menu_items:
            menu.add_row(key, desc)
        
        # Display version and update indicator - force fresh import
        import importlib
        importlib.reload(polyterm)
        version_text = f"[dim]PolyTerm v{polyterm.__version__}[/dim]{update_indicator}"
        
        # No panel borders - just print menu directly
        self.console.print("[bold yellow]Main Menu[/bold yellow]")
        self.console.print(version_text)
        self.console.print()
        self.console.print(menu)
        self.console.print()
    
    def get_choice(self) -> str:
        """Get user menu choice
        
        Returns:
            User's choice as lowercase string
        """
        return self.console.input("[bold cyan]Select an option:[/bold cyan] ").strip().lower()


