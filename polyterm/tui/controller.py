"""TUI Controller - Main application loop"""

from pathlib import Path
from rich.console import Console
from rich.prompt import Confirm
from .logo import display_logo
from .menu import MainMenu
from .screens import (
    monitor_screen,
    live_monitor_screen,
    whales_screen,
    watch_screen,
    analytics_screen,
    portfolio_screen,
    export_screen,
    settings_screen,
    help_screen,
    arbitrage_screen,
    predictions_screen,
    wallets_screen,
    alerts_screen,
    orderbook_screen,
    tutorial_screen,
    glossary_screen,
    simulate_screen,
    run_risk_screen,
    run_follow_screen,
    run_parlay_screen,
    run_bookmarks_screen,
    run_dashboard_screen,
    run_chart_screen,
    run_compare_screen,
    run_size_screen,
    run_recent_screen,
    run_pricealert_screen,
    run_calendar_screen,
    run_fees_screen,
    run_stats_screen,
    run_search_screen,
    run_notes_screen,
    run_position_screen,
    run_presets_screen,
    run_sentiment_screen,
    run_correlate_screen,
    run_exit_screen,
    run_depth_screen,
    run_trade_screen,
    run_timeline_screen,
    run_analyze_screen,
    run_journal_screen,
    run_hot_screen,
    run_pnl_screen,
    run_alertcenter_screen,
    run_groups_screen,
    run_attribution_screen,
    run_snapshot_screen,
    run_signals_screen,
    run_similar_screen,
    run_ladder_screen,
    run_benchmark_screen,
    run_pin_screen,
    run_spread_screen,
    run_history_screen,
    run_streak_screen,
    run_digest_screen,
    run_timing_screen,
    run_odds_screen,
    run_health_screen,
    run_scenario_screen,
    run_watchdog_screen,
    run_volume_screen,
    run_screener_screen,
    run_backtest_screen,
    run_report_screen,
    run_liquidity_screen,
    run_ev_screen,
    run_calibrate_screen,
    run_quick_screen,
    run_leaderboard_screen,
    run_notify_screen,
    run_crypto15m_screen,
    run_mywallet_screen,
    run_quicktrade_screen,
)

# Screen dispatch table: maps shortcut keys to screen functions
# Each screen function takes a single Console argument
SCREEN_ROUTES = {
    # Core screens (numbered)
    '1': monitor_screen, 'mon': monitor_screen,
    '2': live_monitor_screen, 'l': live_monitor_screen,
    '3': whales_screen, 'w': whales_screen,
    '4': watch_screen,
    '5': analytics_screen, 'a': analytics_screen,
    '6': portfolio_screen, 'p': portfolio_screen,
    '7': export_screen, 'e': export_screen,
    '8': settings_screen, 's': settings_screen,
    '9': arbitrage_screen, 'arb': arbitrage_screen,
    '10': predictions_screen, 'pred': predictions_screen,
    '11': wallets_screen, 'wal': wallets_screen,
    '12': alerts_screen, 'alert': alerts_screen,
    '13': orderbook_screen, 'ob': orderbook_screen,
    '14': run_risk_screen, 'risk': run_risk_screen,
    '15': run_follow_screen, 'follow': run_follow_screen, 'copy': run_follow_screen,
    '16': run_parlay_screen, 'parlay': run_parlay_screen,
    '17': run_bookmarks_screen, 'bm': run_bookmarks_screen, 'bookmarks': run_bookmarks_screen,
    # Help and learning
    'h': help_screen, '?': help_screen,
    't': tutorial_screen, 'tut': tutorial_screen, 'tutorial': tutorial_screen,
    'g': glossary_screen, 'gloss': glossary_screen, 'glossary': glossary_screen,
    'sim': simulate_screen, 'simulate': simulate_screen,
    # Dashboard and tools
    'd': run_dashboard_screen, 'dash': run_dashboard_screen, 'dashboard': run_dashboard_screen,
    'ch': run_chart_screen, 'chart': run_chart_screen,
    'cmp': run_compare_screen, 'compare': run_compare_screen,
    'sz': run_size_screen, 'size': run_size_screen,
    'rec': run_recent_screen, 'recent': run_recent_screen,
    'pa': run_pricealert_screen, 'pricealert': run_pricealert_screen,
    'cal': run_calendar_screen, 'calendar': run_calendar_screen,
    'fee': run_fees_screen, 'fees': run_fees_screen,
    'st': run_stats_screen, 'stats': run_stats_screen,
    'sr': run_search_screen, 'search': run_search_screen,
    'nt': run_notes_screen, 'notes': run_notes_screen,
    'pos': run_position_screen, 'position': run_position_screen,
    'pr': run_presets_screen, 'presets': run_presets_screen,
    'sent': run_sentiment_screen, 'sentiment': run_sentiment_screen,
    'corr': run_correlate_screen, 'correlate': run_correlate_screen,
    'ex': run_exit_screen, 'exitplan': run_exit_screen,
    'dp': run_depth_screen, 'depth': run_depth_screen,
    'tr': run_trade_screen, 'trade': run_trade_screen,
    'tl': run_timeline_screen, 'timeline': run_timeline_screen,
    'an': run_analyze_screen, 'analyze': run_analyze_screen,
    'jn': run_journal_screen, 'journal': run_journal_screen,
    'hot': run_hot_screen,
    'pnl': run_pnl_screen,
    'ac': run_alertcenter_screen, 'center': run_alertcenter_screen, 'alertcenter': run_alertcenter_screen,
    'gr': run_groups_screen, 'groups': run_groups_screen,
    'attr': run_attribution_screen, 'attribution': run_attribution_screen,
    'snap': run_snapshot_screen, 'snapshot': run_snapshot_screen,
    'sig': run_signals_screen, 'signals': run_signals_screen,
    'sml': run_similar_screen, 'similar': run_similar_screen,
    'lad': run_ladder_screen, 'ladder': run_ladder_screen,
    'bench': run_benchmark_screen, 'benchmark': run_benchmark_screen,
    'pin': run_pin_screen, 'pinned': run_pin_screen,
    'sp': run_spread_screen, 'spread': run_spread_screen,
    'hist': run_history_screen, 'history': run_history_screen,
    'stk': run_streak_screen, 'streak': run_streak_screen,
    'dig': run_digest_screen, 'digest': run_digest_screen,
    'tm': run_timing_screen, 'timing': run_timing_screen,
    'od': run_odds_screen, 'odds': run_odds_screen,
    'hp': run_health_screen, 'health': run_health_screen,
    'sc': run_scenario_screen, 'scenario': run_scenario_screen,
    'wd': run_watchdog_screen, 'watchdog': run_watchdog_screen,
    'vol': run_volume_screen, 'volume': run_volume_screen,
    'scr': run_screener_screen, 'screener': run_screener_screen,
    'bt': run_backtest_screen, 'backtest': run_backtest_screen,
    'rp': run_report_screen, 'report': run_report_screen,
    'liq': run_liquidity_screen, 'liquidity': run_liquidity_screen,
    'ev': run_ev_screen,
    'cb': run_calibrate_screen, 'calibrate': run_calibrate_screen,
    'qk': run_quick_screen, 'quick': run_quick_screen,
    'lb': run_leaderboard_screen, 'leaderboard': run_leaderboard_screen,
    'nf': run_notify_screen, 'notify': run_notify_screen,
    'c15': run_crypto15m_screen, 'crypto15m': run_crypto15m_screen, '15m': run_crypto15m_screen,
    'mw': run_mywallet_screen, 'mywallet': run_mywallet_screen, 'wallet': run_mywallet_screen,
    'qt': run_quicktrade_screen, 'quicktrade': run_quicktrade_screen,
}

QUIT_COMMANDS = {'q', 'quit', 'exit'}


class TUIController:
    """Main TUI controller and event loop"""

    def __init__(self):
        self.console = Console()
        self.menu = MainMenu()
        self.running = True
        self.onboarded_file = Path.home() / ".polyterm" / ".onboarded"

    def _check_first_run(self) -> bool:
        """Check if this is the user's first run"""
        return not self.onboarded_file.exists()

    def _show_welcome(self):
        """Show welcome message for first-time users"""
        self.console.print()
        self.console.print("[bold cyan]Welcome to PolyTerm![/bold cyan]")
        self.console.print()
        self.console.print("It looks like this is your first time using PolyTerm.")
        self.console.print("We have an interactive tutorial that covers:")
        self.console.print("  - How prediction markets work")
        self.console.print("  - Understanding prices and probabilities")
        self.console.print("  - Tracking whales and smart money")
        self.console.print("  - Finding arbitrage opportunities")
        self.console.print()

        if Confirm.ask("[cyan]Would you like to start the tutorial?[/cyan]", default=True):
            self.console.print()
            tutorial_screen(self.console)
            input("\nPress Enter to continue to the main menu...")
            self.console.clear()
            display_logo(self.console)
        else:
            # Mark as onboarded even if they skip
            self._mark_onboarded()
            self.console.print()
            self.console.print("[dim]No problem! You can run the tutorial anytime by pressing 't'.[/dim]")
            self.console.print("[dim]Press 'g' for a glossary of terms, or 'h' for help.[/dim]")
            self.console.print()
            input("Press Enter to continue...")
            self.console.clear()
            display_logo(self.console)

    def _mark_onboarded(self):
        """Mark the user as onboarded"""
        try:
            self.onboarded_file.parent.mkdir(parents=True, exist_ok=True)
            self.onboarded_file.touch()
        except Exception:
            pass

    def run(self):
        """Main TUI loop - display menu and handle user input"""
        try:
            self.console.clear()
            display_logo(self.console)

            # Check for first-time user
            if self._check_first_run():
                self._show_welcome()

            while self.running:
                self.menu.display()
                choice = self.menu.get_choice()

                # Handle pagination navigation (just redisplay menu)
                if choice in ('_next_page', '_prev_page'):
                    self.console.clear()
                    display_logo(self.console)
                    continue

                # Handle update command (needs special import)
                if choice in ('u', 'update'):
                    from .screens.settings import update_polyterm
                    update_polyterm(self.console)
                # Handle quit
                elif choice in QUIT_COMMANDS:
                    self.quit()
                # Dispatch to screen via lookup table
                elif choice in SCREEN_ROUTES:
                    try:
                        SCREEN_ROUTES[choice](self.console)
                    except KeyboardInterrupt:
                        self.console.print("\n[yellow]Interrupted.[/yellow]")
                    except Exception as e:
                        self.console.print(f"\n[red]Error: {e}[/red]")

                else:
                    self.console.print("[red]Invalid choice. Try again.[/red]")

                # Return to menu (unless quitting)
                if self.running and choice not in QUIT_COMMANDS:
                    # Occasionally show a helpful tip
                    from ..utils.tips import should_show_tip, get_random_tip, format_tip
                    if should_show_tip():
                        tip_contexts = {
                            '1': 'monitor', 'mon': 'monitor',
                            '3': 'whales', 'w': 'whales',
                            '9': 'arbitrage', 'arb': 'arbitrage',
                            '10': 'predict', 'pred': 'predict',
                            '13': 'orderbook', 'ob': 'orderbook',
                            '12': 'alerts', 'alert': 'alerts',
                        }
                        context = tip_contexts.get(choice)
                        tip = get_random_tip(context)
                        self.console.print(f"\n{format_tip(tip)}")

                    input("\nPress Enter to return to menu...")
                    self.console.clear()
                    display_logo(self.console)
                    self.menu.reset_page()  # Reset to page 1 after any screen

        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            self.console.print("\n\n[yellow]Interrupted. Exiting...[/yellow]")
            self.running = False

    def quit(self):
        """Exit TUI with farewell message"""
        self.console.print("\n[yellow]Thanks for using PolyTerm! 📊[/yellow]")
        self.console.print("[dim]Happy trading![/dim]\n")
        self.running = False
