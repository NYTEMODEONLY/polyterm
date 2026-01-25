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

                # Handle menu choices (note: 'm' is now for pagination, use '1' or 'mon' for monitor)
                if choice == '1' or choice == 'mon':
                    monitor_screen(self.console)
                elif choice == '2' or choice == 'l':
                    live_monitor_screen(self.console)
                elif choice == '3' or choice == 'w':
                    whales_screen(self.console)
                elif choice == '4':
                    watch_screen(self.console)
                elif choice == '5' or choice == 'a':
                    analytics_screen(self.console)
                elif choice == '6' or choice == 'p':
                    portfolio_screen(self.console)
                elif choice == '7' or choice == 'e':
                    export_screen(self.console)
                elif choice == '8' or choice == 's':
                    settings_screen(self.console)
                elif choice == '9' or choice == 'arb':
                    arbitrage_screen(self.console)
                elif choice == '10' or choice == 'pred':
                    predictions_screen(self.console)
                elif choice == '11' or choice == 'wal':
                    wallets_screen(self.console)
                elif choice == '12' or choice == 'alert':
                    alerts_screen(self.console)
                elif choice == '13' or choice == 'ob':
                    orderbook_screen(self.console)
                elif choice == 'u' or choice == 'update':
                    # Quick update option
                    from .screens.settings import update_polyterm
                    update_polyterm(self.console)
                elif choice == 'h' or choice == '?':
                    help_screen(self.console)
                elif choice == 't' or choice == 'tut' or choice == 'tutorial':
                    tutorial_screen(self.console)
                elif choice == 'g' or choice == 'gloss' or choice == 'glossary':
                    glossary_screen(self.console)
                elif choice == 'sim' or choice == 'simulate':
                    simulate_screen(self.console)
                elif choice == 'risk' or choice == '14':
                    run_risk_screen(self.console)
                elif choice == 'follow' or choice == 'copy' or choice == '15':
                    run_follow_screen(self.console)
                elif choice == 'parlay' or choice == '16':
                    run_parlay_screen(self.console)
                elif choice == 'bm' or choice == 'bookmarks' or choice == '17':
                    run_bookmarks_screen(self.console)
                elif choice == 'd' or choice == 'dash' or choice == 'dashboard':
                    run_dashboard_screen(self.console)
                elif choice == 'ch' or choice == 'chart':
                    run_chart_screen(self.console)
                elif choice == 'cmp' or choice == 'compare':
                    run_compare_screen(self.console)
                elif choice == 'sz' or choice == 'size':
                    run_size_screen(self.console)
                elif choice == 'rec' or choice == 'recent':
                    run_recent_screen(self.console)
                elif choice == 'pa' or choice == 'pricealert':
                    run_pricealert_screen(self.console)
                elif choice == 'cal' or choice == 'calendar':
                    run_calendar_screen(self.console)
                elif choice == 'fee' or choice == 'fees':
                    run_fees_screen(self.console)
                elif choice == 'st' or choice == 'stats':
                    run_stats_screen(self.console)
                elif choice == 'sr' or choice == 'search':
                    run_search_screen(self.console)
                elif choice == 'nt' or choice == 'notes':
                    run_notes_screen(self.console)
                elif choice == 'pos' or choice == 'position':
                    run_position_screen(self.console)
                elif choice == 'pr' or choice == 'presets':
                    run_presets_screen(self.console)
                elif choice == 'sent' or choice == 'sentiment':
                    run_sentiment_screen(self.console)
                elif choice == 'corr' or choice == 'correlate':
                    run_correlate_screen(self.console)
                elif choice == 'ex' or choice == 'exitplan':
                    run_exit_screen(self.console)
                elif choice == 'dp' or choice == 'depth':
                    run_depth_screen(self.console)
                elif choice == 'tr' or choice == 'trade':
                    run_trade_screen(self.console)
                elif choice == 'tl' or choice == 'timeline':
                    run_timeline_screen(self.console)
                elif choice == 'an' or choice == 'analyze':
                    run_analyze_screen(self.console)
                elif choice == 'jn' or choice == 'journal':
                    run_journal_screen(self.console)
                elif choice == 'hot':
                    run_hot_screen(self.console)
                elif choice == 'pnl':
                    run_pnl_screen(self.console)
                elif choice == 'ac' or choice == 'center' or choice == 'alertcenter':
                    run_alertcenter_screen(self.console)
                elif choice == 'gr' or choice == 'groups':
                    run_groups_screen(self.console)
                elif choice == 'attr' or choice == 'attribution':
                    run_attribution_screen(self.console)
                elif choice == 'snap' or choice == 'snapshot':
                    run_snapshot_screen(self.console)
                elif choice == 'sig' or choice == 'signals':
                    run_signals_screen(self.console)
                elif choice == 'sml' or choice == 'similar':
                    run_similar_screen(self.console)
                elif choice == 'lad' or choice == 'ladder':
                    run_ladder_screen(self.console)
                elif choice == 'bench' or choice == 'benchmark':
                    run_benchmark_screen(self.console)
                elif choice == 'pin' or choice == 'pinned':
                    run_pin_screen(self.console)
                elif choice == 'sp' or choice == 'spread':
                    run_spread_screen(self.console)
                elif choice == 'hist' or choice == 'history':
                    run_history_screen(self.console)
                elif choice == 'stk' or choice == 'streak':
                    run_streak_screen(self.console)
                elif choice == 'dig' or choice == 'digest':
                    run_digest_screen(self.console)
                elif choice == 'tm' or choice == 'timing':
                    run_timing_screen(self.console)
                elif choice == 'od' or choice == 'odds':
                    run_odds_screen(self.console)
                elif choice == 'hp' or choice == 'health':
                    run_health_screen(self.console)
                elif choice == 'sc' or choice == 'scenario':
                    run_scenario_screen(self.console)
                elif choice == 'wd' or choice == 'watchdog':
                    run_watchdog_screen(self.console)
                elif choice == 'vol' or choice == 'volume':
                    run_volume_screen(self.console)
                elif choice == 'scr' or choice == 'screener':
                    run_screener_screen(self.console)
                elif choice == 'bt' or choice == 'backtest':
                    run_backtest_screen(self.console)
                elif choice == 'rp' or choice == 'report':
                    run_report_screen(self.console)
                elif choice == 'liq' or choice == 'liquidity':
                    run_liquidity_screen(self.console)
                elif choice == 'ev':
                    run_ev_screen(self.console)
                elif choice == 'cb' or choice == 'calibrate':
                    run_calibrate_screen(self.console)
                elif choice == 'qk' or choice == 'quick':
                    run_quick_screen(self.console)
                elif choice == 'lb' or choice == 'leaderboard':
                    run_leaderboard_screen(self.console)
                elif choice == 'nf' or choice == 'notify':
                    run_notify_screen(self.console)
                elif choice == 'c15' or choice == 'crypto15m' or choice == '15m':
                    run_crypto15m_screen(self.console)
                elif choice == 'mw' or choice == 'mywallet' or choice == 'wallet':
                    run_mywallet_screen(self.console)
                elif choice == 'qt' or choice == 'quicktrade':
                    run_quicktrade_screen(self.console)
                elif choice == 'q' or choice == 'quit' or choice == 'exit':
                    self.quit()
                else:
                    self.console.print("[red]Invalid choice. Try again.[/red]")
                
                # Return to menu (unless quitting)
                if self.running and choice != 'q' and choice != 'quit' and choice != 'exit':
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


