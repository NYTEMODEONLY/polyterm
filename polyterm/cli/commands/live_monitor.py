"""Live Monitor command - dedicated terminal window for real-time market monitoring"""

import click
import time
import subprocess
import sys
import os
import signal
import atexit
import asyncio
from datetime import datetime, timezone
from typing import Optional, Dict, List, Any
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.align import Align

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...api.aggregator import APIAggregator
from ...core.scanner import MarketScanner
from ...utils.formatting import format_probability_rich, format_volume

try:
    from dateutil import parser as date_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


# Category keywords for filtering - main categories and sub-categories
CATEGORY_KEYWORDS = {
    # Main sports category
    'sports': ['nfl', 'nba', 'mlb', 'nhl', 'super bowl', 'world series', 'playoffs',
               'championship', 'soccer', 'football', 'baseball', 'basketball', 'hockey',
               'tennis', 'golf', 'ufc', 'boxing', 'f1', 'formula 1', 'olympics', 'fifa',
               'premier league', 'world cup', 'mvp', 'coach', 'draft pick', 'trade deadline'],

    # Sports sub-categories
    'nfl': ['nfl', 'super bowl', 'afc', 'nfc', 'touchdown', 'quarterback', 'patriots',
            'chiefs', 'eagles', 'cowboys', 'packers', 'ravens', 'bills', 'dolphins',
            'broncos', 'seahawks', 'rams', '49ers', 'lions', 'bears', 'jets', 'giants',
            'steelers', 'bengals', 'browns', 'texans', 'colts', 'jaguars', 'titans',
            'raiders', 'chargers', 'cardinals', 'falcons', 'panthers', 'saints', 'buccaneers',
            'vikings', 'commanders', 'football'],
    'nba': ['nba', 'basketball', 'lakers', 'celtics', 'warriors', 'nets', 'bucks',
            'heat', 'suns', 'nuggets', 'clippers', 'knicks', 'mavericks', 'grizzlies'],
    'mlb': ['mlb', 'baseball', 'world series', 'yankees', 'dodgers', 'red sox', 'cubs'],
    'nhl': ['nhl', 'hockey', 'stanley cup', 'bruins', 'rangers', 'maple leafs'],
    'soccer': ['soccer', 'premier league', 'world cup', 'fifa', 'champions league',
               'manchester', 'liverpool', 'chelsea', 'arsenal', 'barcelona', 'real madrid'],
    'golf': ['golf', 'pga', 'masters', 'us open', 'british open', 'ryder cup'],
    'tennis': ['tennis', 'wimbledon', 'us open', 'french open', 'australian open', 'grand slam'],
    'ufc': ['ufc', 'mma', 'boxing', 'fight', 'knockout'],
    'f1': ['f1', 'formula 1', 'grand prix', 'nascar', 'racing'],

    # Crypto categories
    'crypto': ['bitcoin', 'btc ', ' btc', 'ethereum', ' eth ', 'solana', ' sol ',
               ' xrp', 'crypto', 'blockchain', 'defi', ' nft', 'coinbase', 'binance'],
    'bitcoin': ['bitcoin', 'btc ', ' btc', 'satoshi', 'btc etf'],
    'ethereum': ['ethereum', ' eth ', ' eth?', 'vitalik', 'eth etf'],
    'solana': ['solana', ' sol '],
    'altcoins': [' xrp', 'ripple', 'cardano', ' ada', 'polkadot', 'avalanche'],

    # Politics categories
    'politics': ['trump', 'biden', 'president', 'election', 'congress', 'senate',
                 'republican', 'democrat', 'governor', 'mayor', 'cabinet'],
    'trump': ['trump', 'donald', 'maga', 'mar-a-lago'],
    'elections': ['election', 'vote', 'ballot', 'primary', 'nominee', 'electoral'],
    'congress': ['congress', 'senate', 'house of rep', 'speaker', 'filibuster'],
}


def matches_category(market: dict, category: str) -> bool:
    """Check if market matches a category using keyword search"""
    import re

    if not category:
        return True

    category_lower = category.lower()

    # First check if API provides category field
    market_category = market.get('category')
    if market_category and category_lower in market_category.lower():
        return True

    # Search in question/title - add spaces for word boundary matching
    title = ' ' + market.get('question', market.get('title', '')).lower() + ' '

    # If category is a predefined one, use keywords
    if category_lower in CATEGORY_KEYWORDS:
        for kw in CATEGORY_KEYWORDS[category_lower]:
            # For short keywords (3 chars or less), use word boundary matching
            if len(kw.strip()) <= 3:
                pattern = r'\b' + re.escape(kw.strip()) + r'\b'
                if re.search(pattern, title):
                    return True
            else:
                if kw in title:
                    return True
        return False

    # Otherwise, do a direct search
    return category_lower in title


class LiveMarketMonitor:
    """Enhanced live market monitor with color-coded indicators and real-time updates"""
    
    def __init__(self, config, market_id: Optional[str] = None, category: Optional[str] = None):
        self.config = config
        self.market_id = market_id
        self.category = category
        self.console = Console(theme=None, force_terminal=True)
        
        # Process tracking for cleanup
        self._live_display = None
        self._running = False
        
        # Register cleanup handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        atexit.register(self.cleanup)
        
        # Initialize clients
        self.gamma_client = GammaClient(
            base_url=config.gamma_base_url,
            api_key=config.gamma_api_key,
        )
        self.clob_client = CLOBClient(
            rest_endpoint=config.clob_rest_endpoint,
            ws_endpoint=config.clob_endpoint,
        )
        self.subgraph_client = SubgraphClient(endpoint=config.subgraph_endpoint)
        
        # Initialize aggregator and scanner
        self.aggregator = APIAggregator(self.gamma_client, self.clob_client, self.subgraph_client)
        self.scanner = MarketScanner(
            self.gamma_client,
            self.clob_client,
            self.subgraph_client,
            check_interval=1,  # 1 second updates for live monitoring
        )
        
        # State tracking for color indicators
        self.previous_data = {}
        self.price_history = {}
        self.volume_history = {}
    
    def _signal_handler(self, signum, frame):
        """Handle interrupt signals"""
        self.console.print(f"\n[yellow]🔴 Received signal {signum}, shutting down gracefully...[/yellow]")
        self._running = False
        self.cleanup()
        sys.exit(0)
        
    def get_color_indicator(self, current: float, previous: float, indicator_type: str = "price") -> str:
        """Get color-coded indicator for changes"""
        if previous is None or previous == 0:
            return "white"
        
        change = current - previous
        change_pct = (change / previous) * 100
        
        if indicator_type == "price":
            if change_pct > 2:
                return "bright_green"
            elif change_pct > 0.5:
                return "green"
            elif change_pct < -2:
                return "bright_red"
            elif change_pct < -0.5:
                return "red"
            else:
                return "yellow"
        elif indicator_type == "volume":
            if change_pct > 50:
                return "bright_blue"
            elif change_pct > 20:
                return "blue"
            elif change_pct < -50:
                return "bright_magenta"
            elif change_pct < -20:
                return "magenta"
            else:
                return "white"
        
        return "white"
    
    def get_change_symbol(self, current: float, previous: float) -> str:
        """Get directional symbol for changes"""
        if previous is None or previous == 0:
            return "●"
        
        change = current - previous
        if change > 0:
            return "▲"
        elif change < 0:
            return "▼"
        else:
            return "●"
    
    def format_price_change(self, current: float, previous: float) -> str:
        """Format price change with color and symbol"""
        if previous is None or previous == 0:
            return f"[white]{current:.2f}[/white]"
        
        change = current - previous
        change_pct = (change / previous) * 100
        color = self.get_color_indicator(current, previous, "price")
        symbol = self.get_change_symbol(current, previous)
        
        return f"[{color}]{symbol} {current:.2f} ({change_pct:+.1f}%)[/{color}]"
    
    def format_volume_change(self, current: float, previous: float) -> str:
        """Format volume change with color and symbol"""
        if previous is None or previous == 0:
            return f"[white]${current:,.0f}[/white]"
        
        change = current - previous
        change_pct = (change / previous) * 100
        color = self.get_color_indicator(current, previous, "volume")
        symbol = self.get_change_symbol(current, previous)
        
        return f"[{color}]{symbol} ${current:,.0f} ({change_pct:+.0f}%)[/{color}]"
    
    def get_market_data(self) -> List[Dict[str, Any]]:
        """Get market data based on current selection"""
        try:
            if self.market_id:
                # Single market monitoring
                market_data = self.gamma_client.get_market(self.market_id)
                return [market_data] if market_data else []
            elif self.category:
                # Category-based monitoring - fetch many markets and filter by keywords
                # API tag parameter doesn't work reliably, so we filter locally
                all_markets = self.gamma_client.get_markets(
                    limit=200,
                    closed=False
                )
                # Filter by category using keyword matching
                filtered = [m for m in all_markets if matches_category(m, self.category)]
                return filtered[:50]  # Return top 50 matching markets
            else:
                # All active markets
                return self.aggregator.get_live_markets(
                    limit=20,
                    require_volume=True,
                    min_volume=0.01
                )
        except Exception as e:
            self.console.print(f"[red]Error fetching market data: {e}[/red]")
            return []
    
    def generate_live_table(self) -> Table:
        """Generate live market table with color indicators"""
        now = datetime.now()
        
        # Create header based on selection
        if self.market_id:
            title = f"🔴 LIVE MARKET MONITOR - Single Market"
        elif self.category:
            title = f"🔴 LIVE MARKET MONITOR - {self.category.upper()} Category"
        else:
            title = f"🔴 LIVE MARKET MONITOR - All Active Markets"
        
        table = Table(
            title=f"{title} (Updated: {now.strftime('%H:%M:%S')})",
            title_style="bold red",
            show_header=True,
            header_style="bold magenta"
        )
        
        # Configure columns
        table.add_column("Market", style="cyan", no_wrap=False, max_width=50)
        table.add_column("Price", justify="right", style="bold")
        table.add_column("24h Volume", justify="right", style="bold")
        table.add_column("Change", justify="right", style="bold")
        table.add_column("Status", justify="center", style="bold")
        
        # Get market data
        markets = self.get_market_data()
        
        for market in markets:
            market_id = market.get("id")
            
            # Get title - prefer question from nested markets array, fallback to title
            title = ""
            if market.get('markets') and len(market.get('markets', [])) > 0:
                title = market['markets'][0].get('question', market.get('title', ''))
            else:
                title = market.get('title', '')
            title = title[:50]
            
            # Get price data from nested markets array
            outcome_prices = None
            if market.get('markets') and len(market.get('markets', [])) > 0:
                outcome_prices = market['markets'][0].get('outcomePrices')
            
            # Parse outcome prices
            if isinstance(outcome_prices, str):
                import json
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = None
            
            if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                current_price = float(outcome_prices[0])
            else:
                current_price = 0
            
            # Get previous price for comparison
            previous_price = self.previous_data.get(market_id, {}).get('price')
            
            # Get volume data
            current_volume = float(market.get('volume24hr', 0) or 0)
            previous_volume = self.previous_data.get(market_id, {}).get('volume')
            
            # Format price with change indicator
            price_text = self.format_price_change(current_price, previous_price)
            
            # Format volume with change indicator
            volume_text = self.format_volume_change(current_volume, previous_volume)
            
            # Calculate overall change
            if previous_price and previous_price > 0:
                price_change_pct = ((current_price - previous_price) / previous_price) * 100
                if price_change_pct > 1:
                    change_text = f"[bright_green]▲ +{price_change_pct:.1f}%[/bright_green]"
                elif price_change_pct < -1:
                    change_text = f"[bright_red]▼ {price_change_pct:.1f}%[/bright_red]"
                else:
                    change_text = f"[yellow]● {price_change_pct:+.1f}%[/yellow]"
            else:
                change_text = "[white]● NEW[/white]"
            
            # Market status
            end_date_str = market.get('endDate', '')
            if end_date_str:
                try:
                    if HAS_DATEUTIL:
                        end_date = date_parser.parse(end_date_str)
                    else:
                        end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    
                    now_utc = datetime.now(timezone.utc)
                    hours_until = (end_date - now_utc).total_seconds() / 3600
                    
                    if hours_until > 24:
                        days_until = int(hours_until / 24)
                        status_text = f"[green]{days_until}d left[/green]"
                    elif hours_until > 0:
                        status_text = f"[yellow]{int(hours_until)}h left[/yellow]"
                    else:
                        status_text = "[red]ENDED[/red]"
                except:
                    status_text = "[dim]?[/dim]"
            else:
                status_text = "[green]ACTIVE[/green]"
            
            # Add row to table
            table.add_row(
                title,
                price_text,
                volume_text,
                change_text,
                status_text
            )
            
            # Store current data for next comparison
            self.previous_data[market_id] = {
                'price': current_price,
                'volume': current_volume,
                'timestamp': now
            }
        
        return table
    
    def run_live_monitor(self):
        """Run the live monitoring loop with real-time trade feeds"""
        self._running = True

        # Stats tracking
        self.trade_count = 0
        self.total_volume = 0.0
        self.buy_count = 0
        self.sell_count = 0
        self.recent_trades = []  # Store last N trades for display
        self.max_recent_trades = 50

        try:
            # Get markets to monitor
            markets_data = self.get_market_data()
            if not markets_data:
                self.console.print(f"[red]❌ No markets found for category: {self.category}[/red]")
                return

            # Extract market slugs for RTDS WebSocket subscription
            market_slugs = []
            market_titles = {}
            market_prices = {}

            for market in markets_data:
                market_slug = market.get("slug")
                market_id = market.get("id")
                title = market.get("question", market.get("title", "Unknown"))
                if market_slug:
                    market_slugs.append(market_slug)
                    market_titles[market_slug] = title
                    if market_id:
                        market_titles[market_id] = title

                # Store initial prices
                outcome_prices = market.get('outcomePrices')
                if isinstance(outcome_prices, str):
                    import json
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except:
                        outcome_prices = None
                if outcome_prices and len(outcome_prices) > 0:
                    market_prices[market_slug or market_id] = float(outcome_prices[0])

            self.market_titles = market_titles
            self.market_prices = market_prices
            self.markets_count = len(market_slugs)

            # Print fixed header (this stays at top)
            self._print_header()

            # Run async WebSocket monitoring with market slugs
            asyncio.run(self._run_websocket_monitor(market_slugs, market_titles))

        except KeyboardInterrupt:
            self.console.print(f"\n[yellow]🔴 Live monitoring stopped[/yellow]")
        except Exception as e:
            self.console.print(f"\n[red]🔴 Live monitoring error: {e}[/red]")
        finally:
            self._running = False
            self.cleanup()

    def _print_header(self):
        """Print the fixed header with metrics"""
        self.console.clear()

        # Category/market info
        if self.category:
            monitor_type = f"Category: {self.category.upper()}"
        elif self.market_id:
            monitor_type = f"Market: {self.market_id[:20]}..."
        else:
            monitor_type = "All Active Markets"

        # Header panel
        header = Panel(
            f"[bold red]🔴 LIVE TRADE MONITOR[/bold red]\n"
            f"[cyan]{monitor_type}[/cyan] | [green]{self.markets_count} markets[/green]\n"
            f"[dim]Press Ctrl+C to stop[/dim]",
            border_style="red",
            padding=(0, 2),
        )
        self.console.print(header)

        # Stats bar (will be updated)
        self._print_stats_bar()

        # Column headers
        self.console.print()
        self.console.print("[bold cyan]TIME     │ MARKET                      │ SIDE      │ SIZE      │ PRICE    │ TOTAL[/bold cyan]")
        self.console.print("[dim]─" * 90 + "[/dim]")

    def _print_stats_bar(self):
        """Print/update the stats bar"""
        stats = (
            f"[bold]Trades:[/bold] {self.trade_count:,} | "
            f"[bold]Volume:[/bold] ${self.total_volume:,.0f} | "
            f"[green]Buys:[/green] {self.buy_count} | "
            f"[red]Sells:[/red] {self.sell_count}"
        )
        self.console.print(f"[on black] {stats} [/on black]")

    async def _run_websocket_monitor(self, market_slugs: List[str], market_titles: Dict[str, str]):
        """Run WebSocket monitoring for live trades"""
        try:
            # Connect to WebSocket
            await self.clob_client.connect_websocket()
            self.console.print("[green]✅ Connected to PolyMarket RTDS WebSocket[/green]")
            
            # Subscribe to trade feeds
            await self.clob_client.subscribe_to_trades(market_slugs, lambda trade: self._handle_trade(trade, market_titles))
            self.console.print(f"[green]✅ Subscribed to {len(market_slugs)} market feeds[/green]")
            self.console.print()
            self.console.print("[bold]🔴 LIVE TRADES (Real-time):[/bold]")
            self.console.print("=" * 80)
            
            # Start listening for trades
            await self.clob_client.listen_for_trades()
            
        except Exception as e:
            self.console.print(f"[red]❌ WebSocket error: {e}[/red]")
            # Fallback to polling mode
            self.console.print("[yellow]⚠️ Falling back to polling mode...[/yellow]")
            await self._run_polling_monitor(market_slugs, market_titles)
        finally:
            await self.clob_client.close_websocket()

    async def _handle_trade(self, trade_data: Dict[str, Any], market_titles: Dict[str, str]):
        """Handle incoming trade data from RTDS"""
        try:
            timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")

            # RTDS format: {topic, type, payload: {eventSlug, slug, price, size, side, ...}}
            payload = trade_data.get("payload", {})
            if not payload:
                return

            # Extract market identifiers
            event_slug = payload.get("eventSlug", "")
            market_slug = payload.get("slug", "")

            market_title = (
                market_titles.get(event_slug) or
                market_titles.get(market_slug) or
                payload.get("title", "Unknown Market")
            )

            # Extract trade details
            size = float(payload.get("size", 0))
            price = float(payload.get("price", 0))
            side = payload.get("side", "").upper()
            outcome = payload.get("outcome", "")

            # Update stats
            self.trade_count += 1
            notional = size * price
            self.total_volume += notional
            if side == "BUY":
                self.buy_count += 1
            else:
                self.sell_count += 1

            # Format and display trade
            side_color = "green" if side == "BUY" else "red"
            side_icon = "🟢" if side == "BUY" else "🔴"
            title_short = market_title[:27] + "..." if len(market_title) > 27 else market_title.ljust(30)
            outcome_str = f"({outcome})" if outcome else ""

            trade_line = (
                f"[dim]{timestamp}[/dim] │ "
                f"{title_short} │ "
                f"[{side_color}]{side_icon} {side:<4} {outcome_str:<5}[/{side_color}] │ "
                f"{size:>8,.0f} │ "
                f"${price:>6.3f} │ "
                f"[bold]${notional:>8,.0f}[/bold]"
            )
            self.console.print(trade_line)

        except Exception as e:
            # Silently ignore parse errors for non-trade messages
            pass

    async def _run_polling_monitor(self, market_slugs: List[str], market_titles: Dict[str, str]):
        """Fallback polling mode when WebSocket fails"""
        self.console.print("[yellow]📊 Polling mode - checking for changes every 2 seconds...[/yellow]")
        
        last_prices = {}
        
        while self._running:
            try:
                markets = self.get_market_data()
                current_time = datetime.now(timezone.utc).strftime("%H:%M:%S")
                
                for market in markets:
                    market_id = market.get("id")
                    if not market_id:
                        continue
                    
                    # Get current price
                    current_price = self._get_market_values(market)['price']
                    previous_price = last_prices.get(market_id)
                    
                    if previous_price is not None and current_price != previous_price:
                        # Price changed - simulate a trade
                        direction = "🟢 BUY" if current_price > previous_price else "🔴 SELL"
                        color = "green" if current_price > previous_price else "red"
                        
                        market_title = market_titles.get(market_id, "Unknown")
                        title_short = market_title[:30] + "..." if len(market_title) > 30 else market_title
                        
                        self.console.print(
                            f"[{color}]{current_time} | {title_short:<33} | {direction} | "
                            f"PRICE CHANGE | ${previous_price:.4f} → ${current_price:.4f}[/{color}]"
                        )
                    
                    last_prices[market_id] = current_price
                
                await asyncio.sleep(2)  # Poll every 2 seconds
                
            except Exception as e:
                if self._running:
                    self.console.print(f"[red]{datetime.now(timezone.utc).strftime('%H:%M:%S')} | ERROR: {e}[/red]")
                await asyncio.sleep(5)
    
    def cleanup(self):
        """Clean up resources and ensure complete termination"""
        try:
            # Stop the running flag
            self._running = False

            # Clear the live display
            if self._live_display:
                self._live_display.stop()
                self._live_display = None

            # Clear console output
            self.console.clear()

            # Close API clients
            if hasattr(self.gamma_client, 'close'):
                self.gamma_client.close()
            if hasattr(self.clob_client, 'close'):
                self.clob_client.close()
            if hasattr(self.subgraph_client, 'close'):
                self.subgraph_client.close()

            # Clear state data
            self.previous_data.clear()
            self.price_history.clear()
            self.volume_history.clear()

            # Clean up temporary script file
            script_path = "/tmp/polyterm_live_monitor.py"
            try:
                if os.path.exists(script_path):
                    os.remove(script_path)
            except:
                pass

            # Force garbage collection
            import gc
            gc.collect()

        except Exception as e:
            # Don't let cleanup errors prevent termination
            pass

        # Force exit to ensure complete termination
        try:
            os._exit(0)
        except:
            sys.exit(0)

    def _get_market_values(self, market):
        """Get comparable values from market data"""
        try:
            # Get title
            title = ""
            if market.get('markets') and len(market.get('markets', [])) > 0:
                title = market['markets'][0].get('question', market.get('title', ''))
            else:
                title = market.get('title', '')

            # Get price and volume
            price = 0
            if market.get('markets') and len(market.get('markets', [])) > 0:
                outcome_prices = market['markets'][0].get('outcomePrices')
                if isinstance(outcome_prices, str):
                    import json
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except:
                        outcome_prices = None
                if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                    price = float(outcome_prices[0])

            volume = float(market.get('volume24hr', 0) or 0)

            return {
                'title': title[:30],  # Truncate for display
                'price': price,
                'volume': volume
            }
        except Exception:
            return {'title': 'Unknown', 'price': 0, 'volume': 0}

    def _get_change_direction(self, old_values, new_values):
        """Determine if price/volume changed up or down"""
        try:
            if new_values['price'] > old_values['price']:
                return "↗ UP"
            elif new_values['price'] < old_values['price']:
                return "↘ DOWN"
            elif new_values['volume'] > old_values['volume']:
                return "📊 VOL+"
            else:
                return "→ SAME"
        except:
            return "→ CHG"

    def _print_market_update(self, market, timestamp, direction):
        """Print a single market update in log format"""
        try:
            values = self._get_market_values(market)

            # Format price and volume
            price_str = ".4f" if values['price'] < 1 else ".2f"
            price_display = f"${values['price']:{price_str}}"

            volume_display = ".0f"
            if values['volume'] < 1000:
                volume_display = ".0f"
            elif values['volume'] < 1000000:
                volume_display = ".0f"
                values['volume'] /= 1000
                volume_display += "K"
            else:
                volume_display = ".1f"
                values['volume'] /= 1000000
                volume_display += "M"

            # Format volume properly
            volume_value = values['volume']
            if volume_value < 1000:
                volume_str = f"${volume_value:.0f}"
            elif volume_value < 1000000:
                volume_str = f"${volume_value/1000:.0f}K"
            else:
                volume_str = f"${volume_value/1000000:.1f}M"

            # Color code based on direction
            if "UP" in direction:
                color = "green"
            elif "DOWN" in direction:
                color = "red"
            elif "VOL+" in direction:
                color = "yellow"
            else:
                color = "blue"

            self.console.print(f"[{color}]{timestamp} | {values['title'][:25]:<25} | {price_display:>8} | {volume_str:>8} | {direction}[/{color}]")

        except Exception as e:
            self.console.print(f"[red]{timestamp} | ERROR formatting market: {e}[/red]")


@click.command()
@click.option("--market", help="Market ID or slug to monitor")
@click.option("--category", help="Category to monitor (crypto, politics, sports, etc.)")
@click.option("--interactive", is_flag=True, help="Interactive market/category selection")
@click.pass_context
def live_monitor(ctx, market, category, interactive):
    """Launch dedicated live market monitor in new terminal window"""
    
    config = ctx.obj["config"]
    
    if interactive:
        # Interactive selection mode
        console = Console()
        console.print(Panel("[bold]🔴 Live Market Monitor Setup[/bold]", style="red"))
        console.print()
        
        # Market/Category selection
        console.print("[cyan]Select monitoring mode:[/cyan]")
        console.print("1. Monitor specific market")
        console.print("2. Monitor category (crypto, politics, sports, etc.)")
        console.print("3. Monitor all active markets")
        
        choice = click.prompt("Enter choice (1-3)", type=int, default=1)
        
        if choice == 1:
            # Market selection
            market_search = click.prompt("Enter market ID, slug, or search term")
            
            # Try to find market
            try:
                gamma_client = GammaClient(
                    base_url=config.gamma_base_url,
                    api_key=config.gamma_api_key,
                )
                
                # Try as ID/slug first
                try:
                    market_data = gamma_client.get_market(market_search)
                    market_id = market_data.get("id")
                    market_title = market_data.get("question")
                except:
                    # Search by term
                    results = gamma_client.search_markets(market_search, limit=10)
                    if not results:
                        console.print(f"[red]No markets found for: {market_search}[/red]")
                        return
                    
                    # Show options
                    console.print("\n[yellow]Multiple markets found:[/yellow]")
                    for i, m in enumerate(results):
                        console.print(f"  {i+1}. {m.get('question')}")
                    
                    choice = click.prompt("Select market number", type=int, default=1)
                    selected = results[choice - 1]
                    market_id = selected.get("id")
                    market_title = selected.get("question")
                
                console.print(f"\n[green]Selected:[/green] {market_title}")
                market = market_id
                
            except Exception as e:
                console.print(f"[red]Error finding market: {e}[/red]")
                return
        
        elif choice == 2:
            # Category selection
            console.print("\n[cyan]Available categories:[/cyan]")
            
            categories = ["crypto", "politics", "sports", "economics", "entertainment", "other"]
            
            for i, cat in enumerate(categories, 1):
                console.print(f"  {i}. {cat}")
            console.print()
            
            try:
                cat_choice = click.prompt("Select category (1-6)", type=int, default=1)
                if 1 <= cat_choice <= len(categories):
                    category = categories[cat_choice - 1]
                else:
                    console.print("[red]Invalid choice. Using 'crypto' as default.[/red]")
                    category = "crypto"
            except ValueError:
                console.print("[red]Invalid input. Using 'crypto' as default.[/red]")
                category = "crypto"
            
            console.print(f"\n[green]Selected category:[/green] {category}")
        
        else:
            # All markets
            console.print("\n[green]Monitoring all active markets[/green]")
    
    # Launch live monitor in new terminal
    if market or category:
        # Create monitor instance
        monitor = LiveMarketMonitor(config, market_id=market, category=category)
        
        # Launch in new terminal window
        script_content = f'''
from polyterm.cli.commands.live_monitor import LiveMarketMonitor
from polyterm.utils.config import Config

# Load config
config = Config()

# Create and run monitor
monitor = LiveMarketMonitor(config, market_id="{market or ''}", category="{category or ''}")
monitor.run_live_monitor()
'''
        
        # Write temporary script
        script_path = "/tmp/polyterm_live_monitor.py"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Launch in new terminal
        if sys.platform == "darwin":  # macOS
            subprocess.run([
                "osascript", "-e",
                f'tell app "Terminal" to do script "{sys.executable} {script_path}"'
            ], timeout=10)
        elif sys.platform.startswith("linux"):  # Linux
            subprocess.Popen([
                "gnome-terminal", "--", "python3", script_path
            ])
        else:  # Windows
            subprocess.Popen([
                "start", "cmd", "/k", f"python {script_path}"
            ])
        
        console.print(f"\n[green]🔴 Live monitor launched in new terminal window![/green]")
        console.print("[dim]Close the terminal window or press Ctrl+C to stop monitoring[/dim]")
    
    else:
        console.print("[red]Please specify --market, --category, or use --interactive mode[/red]")
