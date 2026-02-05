"""Main Menu for PolyTerm TUI"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import polyterm
import requests
import re
from packaging import version


class MainMenu:
    """Main menu display and input handler with pagination"""

    def __init__(self):
        self.console = Console()
        self.current_page = 1
        self.total_pages = 2
    
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
    
    def _get_installed_version_pipx(self) -> str:
        """Get the currently installed version from pipx"""
        import subprocess
        try:
            result = subprocess.run(["pipx", "list"], capture_output=True, text=True)
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if 'polyterm' in line.lower():
                        # Parse "package polyterm 0.4.2, installed using..."
                        match = re.search(r'polyterm\s+(\d+\.\d+\.\d+)', line)
                        if match:
                            return match.group(1)
        except Exception:
            pass
        return ""

    def quick_update(self) -> bool:
        """Perform a quick update from the main menu with auto-restart

        Returns:
            True if update was successful, False otherwise
        """
        try:
            import subprocess
            import sys
            import shutil
            import os

            self.console.print("\n[bold green]🔄 Quick Update Starting...[/bold green]")

            # Get latest version from PyPI
            latest_version = None
            try:
                response = requests.get("https://pypi.org/pypi/polyterm/json", timeout=5)
                if response.status_code == 200:
                    latest_version = response.json()["info"]["version"]
            except Exception:
                pass

            has_pipx = False
            has_pip = False

            # Check for pipx first (preferred)
            try:
                subprocess.run(["pipx", "--version"], capture_output=True, check=True)
                has_pipx = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            # Check for pip
            try:
                subprocess.run([sys.executable, "-m", "pip", "--version"], capture_output=True, check=True)
                has_pip = True
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

            update_success = False

            if has_pipx:
                self.console.print("[dim]Using pipx to update...[/dim]")

                # First try pipx upgrade
                result = subprocess.run(["pipx", "upgrade", "polyterm"], capture_output=True, text=True)

                # Verify the upgrade actually worked
                installed_version = self._get_installed_version_pipx()
                if latest_version and installed_version == latest_version:
                    update_success = True
                    self.console.print(f"[green]✓ Upgraded to {installed_version}[/green]")
                else:
                    # pipx upgrade didn't work, try reinstall
                    self.console.print("[yellow]pipx upgrade didn't work, trying reinstall...[/yellow]")
                    subprocess.run(["pipx", "uninstall", "polyterm"], capture_output=True, text=True)
                    # Use --no-cache-dir to avoid pip caching old versions
                    result = subprocess.run(
                        ["pipx", "install", "polyterm", "--pip-args=--no-cache-dir"],
                        capture_output=True, text=True
                    )

                    if result.returncode == 0:
                        installed_version = self._get_installed_version_pipx()
                        if latest_version and installed_version == latest_version:
                            update_success = True
                            self.console.print(f"[green]✓ Reinstalled to {installed_version}[/green]")

            if not update_success and has_pip:
                self.console.print("[dim]Using pip to update...[/dim]")
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "--upgrade", "polyterm"],
                    capture_output=True, text=True
                )
                if result.returncode == 0:
                    update_success = True

            if update_success:
                self.console.print(f"[bold green]✅ Update successful![/bold green]")
                if latest_version:
                    self.console.print(f"[green]Updated to version {latest_version}[/green]")
                self.console.print()

                # Ask user if they want to restart
                self.console.print("[bold cyan]Would you like to restart PolyTerm now?[/bold cyan]")
                self.console.print("[dim]Restarting is required to use the new version.[/dim]")
                self.console.print()
                restart = self.console.input("[cyan]Restart now? (Y/n):[/cyan] ").strip().lower()

                if restart != 'n':
                    self.console.print()
                    self.console.print("[green]🔄 Restarting PolyTerm...[/green]")
                    self.console.print()

                    # Use os.execv to replace current process with new polyterm
                    polyterm_path = shutil.which("polyterm")

                    if polyterm_path:
                        os.execv(polyterm_path, ["polyterm"])
                    else:
                        # Fallback: try running as module
                        os.execv(sys.executable, [sys.executable, "-m", "polyterm"])
                else:
                    self.console.print()
                    self.console.print("[yellow]Update installed but not active.[/yellow]")
                    self.console.print("[dim]Please restart PolyTerm manually to use the new version.[/dim]")

                return True
            else:
                self.console.print("[bold red]❌ Update failed[/bold red]")
                self.console.print("[yellow]Try: pipx uninstall polyterm && pipx install polyterm[/yellow]")
                return False

        except Exception as e:
            self.console.print(f"[bold red]❌ Update error: {e}[/bold red]")
            return False
    
    def display(self):
        """Display paginated main menu"""
        # Check for updates first
        update_indicator, latest_version = self.check_for_updates()
        has_update = bool(latest_version)

        # Page 1: Core Features (fits comfortably on screen)
        page1_items = [
            ("1", "📊 Monitor Markets", "Real-time market tracking"),
            ("2", "🔴 Live Monitor", "Live trades in new window"),
            ("3", "🐋 Whale Activity", "High-volume market moves"),
            ("4", "👁  Watch Market", "Track specific market"),
            ("5", "📈 Market Analytics", "Trends and predictions"),
            ("6", "💼 Portfolio", "View your positions"),
            ("7", "📤 Export Data", "Export to JSON/CSV"),
            ("8", "⚙️  Settings", "Configuration"),
            ("", "", ""),
            ("d", "📊 Dashboard", "Quick overview"),
            ("t", "📚 Tutorial", "Learn the basics"),
            ("h", "❓ Help", "View documentation"),
            ("q", "🚪 Quit", "Exit PolyTerm"),
        ]

        # Page 2: Advanced Features
        page2_items = [
            ("9", "💰 Arbitrage", "Scan for opportunities"),
            ("10", "📈 Predictions", "Signal-based analysis"),
            ("11", "👛 Wallets", "Smart money tracking"),
            ("12", "🔔 Alerts", "Manage notifications"),
            ("13", "📖 Order Book", "Analyze market depth"),
            ("14", "🛡️  Risk", "Risk assessment"),
            ("15", "👥 Copy Trading", "Follow wallets"),
            ("16", "🎰 Parlay", "Combine multiple bets"),
            ("17", "🔖 Bookmarks", "Saved markets"),
            ("", "", ""),
            ("c15", "₿ 15M Crypto", "Short-term crypto"),
            ("mw", "👛 My Wallet", "Your wallet activity"),
            ("qt", "⚡ Quick Trade", "Trade analysis + links"),
            ("", "", ""),
            ("g", "📖 Glossary", "Market terminology"),
            ("sim", "🧮 Simulate", "P&L calculator"),
        ]

        # Add update option if available
        if has_update:
            page1_items.insert(-4, ("u", "🔄 Update", f"Update to v{latest_version}"))

        # Select items for current page
        if self.current_page == 1:
            menu_items = page1_items
            nav_hint = "[yellow]Press [bold cyan]m[/bold cyan] for more options →[/yellow]"
        else:
            menu_items = page2_items
            nav_hint = "[yellow]← Press [bold cyan]b[/bold cyan] to go back[/yellow]"

        # Build menu table
        menu = Table.grid(padding=(0, 2))
        menu.add_column(style="cyan bold", justify="right", width=4)
        menu.add_column(style="white bold", width=22, no_wrap=True)
        menu.add_column(style="bright_black")

        for key, name, desc in menu_items:
            menu.add_row(key, name, desc)

        # Display version and update indicator
        import importlib
        importlib.reload(polyterm)
        version_text = f"[dim]PolyTerm v{polyterm.__version__}[/dim]{update_indicator}"

        # Print menu
        self.console.print("[bold yellow]Main Menu[/bold yellow]", end="")
        self.console.print(f"  [dim](Page {self.current_page}/{self.total_pages})[/dim]")
        self.console.print(version_text)
        self.console.print()
        self.console.print(menu)
        self.console.print()
        self.console.print(nav_hint)
        self.console.print()
    
    def get_choice(self) -> str:
        """Get user menu choice, handling pagination navigation

        Returns:
            User's choice as lowercase string, or special values:
            - "_next_page" to show next page
            - "_prev_page" to show previous page
        """
        choice = self.console.input("[bold cyan]Select an option:[/bold cyan] ").strip().lower()

        # Handle pagination navigation
        if choice in ('m', 'more', '+', 'next'):
            if self.current_page < self.total_pages:
                self.current_page += 1
            return "_next_page"
        elif choice in ('b', 'back', '-', 'prev'):
            if self.current_page > 1:
                self.current_page -= 1
            return "_prev_page"

        return choice

    def reset_page(self):
        """Reset to first page"""
        self.current_page = 1


