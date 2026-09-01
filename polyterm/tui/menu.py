"""Main Menu for PolyTerm TUI"""

from rich.console import Console
from rich.table import Table
import polyterm
from ..utils.errors import handle_api_error


class MainMenu:
    """Main menu display and input handler with pagination"""

    def __init__(self):
        self.console = Console()
        self.current_page = 1
        self.total_pages = 2
        self._update_cache = None  # Cached update check result

    def check_for_updates(self) -> tuple[str, str]:
        """Check GitHub tags/releases for a newer version than the install.

        Cached for this menu session so GitHub is not queried on every
        keypress. Network failure returns empty strings and never crashes
        the menu. Does not query PyPI.

        Returns:
            ``(indicator, latest_version)``. ``latest_version`` is set only
            when GitHub has a newer tag/release than ``polyterm.__version__``.
            Install from the Update row, Settings option 6, or
            ``polyterm update``.
        """
        if self._update_cache is not None:
            return self._update_cache
        try:
            from ..utils.github_update import newer_github_version

            latest = newer_github_version(polyterm.__version__)
            if latest:
                indicator = (
                    f" [bold green]🔄 Update Available: v{latest}[/bold green]"
                )
                self._update_cache = (indicator, latest)
            else:
                self._update_cache = ("", "")
        except Exception:
            self._update_cache = ("", "")
        return self._update_cache

    def quick_update(self) -> bool:
        """Reinstall from GitHub main using the Settings update flow.

        Returns:
            True if update was successful, False otherwise
        """
        try:
            from .screens.settings import update_polyterm

            return update_polyterm(self.console)
        except Exception as e:
            handle_api_error(self.console, e, "menu")
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
            ("3", "🐋 Whale Activity", "Volume heuristic; --wallets for traders"),
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


