"""Orderbook Screen - Order book analysis and visualization with live WebSocket feed"""

import asyncio
import os
import select
import subprocess
import sys
import termios
import threading
import time
import tty
from datetime import datetime
from typing import Optional, Dict, Any

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.layout import Layout
from rich.live import Live
from rich.table import Table
from rich.text import Text

from .market_picker import pick_market, get_market_id, get_market_title
from ...api.clob import CLOBClient
from ...core.orderbook import OrderBookAnalyzer, LiveOrderBook
from ...utils.config import Config
from ...utils.errors import handle_api_error


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _spread_color(spread_pct: float) -> str:
    """Return a Rich color name based on spread width."""
    if spread_pct < 1.0:
        return "green"
    elif spread_pct < 3.0:
        return "yellow"
    return "red"


def _direction_indicator(current: float, previous: Optional[float]) -> str:
    """Return a colored directional arrow for price movement."""
    if previous is None or previous == 0:
        return "[white]--[/white]"
    diff = current - previous
    pct = (diff / previous) * 100
    if diff > 0:
        return f"[green]▲ +{pct:.2f}%[/green]"
    elif diff < 0:
        return f"[red]▼ {pct:.2f}%[/red]"
    return f"[yellow]● 0.00%[/yellow]"


def _depth_bar(size: float, max_size: float, max_width: int, color: str) -> Text:
    """Build a Rich Text bar proportional to size."""
    if max_size <= 0:
        return Text("")
    bar_len = int((size / max_size) * max_width)
    bar_len = max(bar_len, 0)
    txt = Text("█" * bar_len, style=color)
    return txt


# ---------------------------------------------------------------------------
# Live Orderbook Display
# ---------------------------------------------------------------------------

class LiveOrderbookDisplay:
    """Rich Live display for a real-time WebSocket-fed order book."""

    DEPTH_CHOICES = [10, 20, 50]

    def __init__(
        self,
        console: RichConsole,
        market_id: str,
        market_title: str,
        depth: int = 20,
    ):
        self.console = console
        self.market_id = market_id
        self.market_title = market_title
        self.depth = depth
        self._depth_idx = self.DEPTH_CHOICES.index(depth) if depth in self.DEPTH_CHOICES else 1
        self.paused = False

        # Price tracking
        self._initial_price: Optional[float] = None
        self._prev_price: Optional[float] = None

        # WS status
        self._ws_status = "connecting"
        self._stop_event = threading.Event()
        self._live_book: Optional[LiveOrderBook] = None
        self._analyzer: Optional[OrderBookAnalyzer] = None
        self._clob: Optional[CLOBClient] = None
        # Resolution
        self._resolution_data: Optional[Dict[str, Any]] = None

    # -- Rendering -----------------------------------------------------------

    def _render(self) -> Panel:
        """Build the full Rich renderable for one refresh cycle."""
        twidth = self.console.size.width
        half = max((twidth - 6) // 2, 20)

        # Header
        status_icon = {"connected": "[green]● Connected[/green]",
                       "connecting": "[yellow]● Connecting...[/yellow]",
                       "reconnecting": "[yellow]● Reconnecting...[/yellow]",
                       "polling": "[red]● REST fallback[/red]",
                       "disconnected": "[dim]● Disconnected[/dim]"}
        ws_label = status_icon.get(self._ws_status, "[dim]● Unknown[/dim]")
        pause_label = "[yellow]PAUSED[/yellow] " if self.paused else ""
        controls = "[dim][P]ause  [D]epth  [Q]uit[/dim]"
        header_text = (
            f"{pause_label}{ws_label} | Depth: {self.depth} | {controls}"
        )

        # Resolution banner
        if self._resolution_data:
            outcome = self._resolution_data.get("outcome", "")
            color = "green" if outcome == "YES" else "red" if outcome == "NO" else "yellow"
            ws_label = f"[bold {color}]RESOLVED: {outcome}[/bold {color}]"
            header_text = f"{ws_label} | {controls}"

        # Check if we have data
        if self._live_book is None or not self._live_book.is_ready:
            body = Text("Waiting for order book data...", style="dim")
            return Panel(
                body,
                title=f"[bold cyan]Live Order Book — {self.market_title[:50]}[/bold cyan]",
                subtitle=header_text,
                border_style="cyan",
                padding=(1, 2),
            )

        # Gather data
        tob = self._live_book.get_top_of_book()
        depth_data = self._live_book.get_depth(levels=self.depth)
        bids = depth_data["bids"]
        asks = depth_data["asks"]

        # Track prices
        ltp = tob.get("last_trade_price")
        if ltp is not None:
            if self._initial_price is None:
                self._initial_price = ltp

        # --- Depth table ---
        max_bid_size = max((float(b["size"]) for b in bids), default=1)
        max_ask_size = max((float(a["size"]) for a in asks), default=1)
        max_size = max(max_bid_size, max_ask_size)
        bar_width = max(half // 3, 5)

        table = Table(show_header=True, header_style="bold", expand=True,
                      padding=(0, 1), show_edge=False)
        table.add_column("Depth", justify="left", style="green", no_wrap=True, width=bar_width + 1)
        table.add_column("Size", justify="right", style="green", width=10)
        table.add_column("Bid", justify="right", style="green bold", width=9)
        table.add_column("Ask", justify="left", style="red bold", width=9)
        table.add_column("Size", justify="left", style="red", width=10)
        table.add_column("Depth", justify="right", style="red", no_wrap=True, width=bar_width + 1)

        rows = max(len(bids), len(asks))
        for i in range(min(rows, self.depth)):
            # Bid side
            if i < len(bids):
                bp = float(bids[i]["price"])
                bs = float(bids[i]["size"])
                bid_bar = _depth_bar(bs, max_size, bar_width, "green")
                bid_price = f"${bp:.4f}"
                bid_size = f"{bs:,.0f}"
            else:
                bid_bar = Text("")
                bid_price = ""
                bid_size = ""

            # Ask side
            if i < len(asks):
                ap = float(asks[i]["price"])
                as_ = float(asks[i]["size"])
                ask_bar = _depth_bar(as_, max_size, bar_width, "red")
                ask_price = f"${ap:.4f}"
                ask_size = f"{as_:,.0f}"
            else:
                ask_bar = Text("")
                ask_price = ""
                ask_size = ""

            table.add_row(bid_bar, bid_size, bid_price, ask_price, ask_size, ask_bar)

        # --- Footer metrics ---
        best_bid = tob.get("best_bid")
        best_ask = tob.get("best_ask")
        spread = tob.get("spread")
        mid = tob.get("mid_price")

        bid_depth_total = depth_data.get("bid_depth", 0)
        ask_depth_total = depth_data.get("ask_depth", 0)
        total_depth = bid_depth_total + ask_depth_total
        imbalance = (bid_depth_total - ask_depth_total) / total_depth if total_depth else 0

        # Spread line
        spread_val = f"${spread:.4f}" if spread is not None else "—"
        spread_pct = (spread / mid * 100) if spread is not None and mid else 0
        sc = _spread_color(spread_pct)
        spread_line = f"[{sc}]Spread: {spread_val} ({spread_pct:.2f}%)[/{sc}]"

        # Mid price
        mid_str = f"${mid:.4f}" if mid is not None else "—"

        # Depth totals
        depth_line = (
            f"[green]Bid Depth: {bid_depth_total:,.0f}[/green] | "
            f"[red]Ask Depth: {ask_depth_total:,.0f}[/red]"
        )

        # Imbalance bar
        imb_count = int(abs(imbalance) * 10)
        imb_side = "BIDS" if imbalance > 0 else "ASKS"
        imb_color = "green" if imbalance > 0 else "red"
        imb_bar = "█" * imb_count
        imbalance_line = f"Imbalance: [{imb_color}]{imbalance:+.2f} {imb_bar} {imb_side}[/{imb_color}]"

        # Last trade price
        ltp_str = f"${ltp:.4f}" if ltp is not None else "—"
        direction = _direction_indicator(ltp, self._prev_price) if ltp is not None else ""
        session_dir = _direction_indicator(ltp, self._initial_price) if ltp is not None and self._initial_price is not None else ""
        ltp_line = f"Last: {ltp_str} {direction}"
        if session_dir:
            ltp_line += f"  (session: {session_dir})"

        # Update prev price for next render
        if ltp is not None:
            self._prev_price = ltp

        # Messages count
        msg_count = self._live_book.message_count
        last_upd = self._live_book.last_update
        ts_str = last_upd.strftime("%H:%M:%S") if last_upd else "—"

        footer_text = (
            f"{spread_line} | Mid: {mid_str}\n"
            f"{depth_line}\n"
            f"{imbalance_line}\n"
            f"{ltp_line}\n"
            f"[dim]Updated: {ts_str} | Messages: {msg_count}[/dim]"
        )

        # Compose layout
        layout = Table.grid(expand=True)
        layout.add_row(table)
        layout.add_row(Text(""))
        layout.add_row(Text.from_markup(footer_text))

        return Panel(
            layout,
            title=f"[bold cyan]Live Order Book — {self.market_title[:50]}[/bold cyan]",
            subtitle=header_text,
            border_style="cyan",
            padding=(0, 1),
        )

    # -- WS background loop --------------------------------------------------

    def _run_ws_loop(self):
        """Run the async WS event loop in a background thread."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _run():
            def _on_resolution(data):
                self._resolution_data = data

            await self._analyzer.start_live_feed(
                [self.market_id], on_resolution=_on_resolution,
            )
            self._ws_status = "connected"
            try:
                await self._clob.listen_orderbook(
                    max_reconnects=10,
                    message_timeout=60.0,
                )
            except Exception:
                pass

        task = loop.create_task(_run())

        async def _wait_for_stop():
            while not self._stop_event.is_set():
                await asyncio.sleep(0.25)
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            await self._clob.close_websocket()

        try:
            loop.run_until_complete(_wait_for_stop())
        except Exception:
            pass
        finally:
            loop.close()

    # -- REST fallback -------------------------------------------------------

    def _rest_refresh(self):
        """Fetch a REST snapshot and populate the live book manually."""
        try:
            book = self._clob.get_order_book(self.market_id, depth=max(self.DEPTH_CHOICES))
            # Push as a synthetic 'book' message
            self._live_book.handle_message({
                "type": "book",
                "market": self.market_id,
                "bids": book.get("bids", []),
                "asks": book.get("asks", []),
            })
        except Exception:
            pass

    # -- Keyboard input ------------------------------------------------------

    @staticmethod
    def _read_key(timeout: float = 0.1) -> Optional[str]:
        """Non-blocking single-key read from stdin."""
        try:
            if select.select([sys.stdin], [], [], timeout)[0]:
                return sys.stdin.read(1)
        except Exception:
            pass
        return None

    # -- Main entry point ----------------------------------------------------

    def run(self):
        """Run the live orderbook display until the user quits."""
        config = Config()
        self._clob = CLOBClient(rest_endpoint=config.clob_rest_endpoint)
        self._analyzer = OrderBookAnalyzer(self._clob)
        self._live_book = LiveOrderBook(self.market_id)
        self._analyzer._live_books[self.market_id] = self._live_book

        # Try WS first
        ws_thread = threading.Thread(target=self._run_ws_loop, daemon=True)
        ws_thread.start()

        # Wait for first data (up to 8 seconds)
        waited = 0.0
        while not self._live_book.is_ready and waited < 8.0:
            time.sleep(0.25)
            waited += 0.25

        # If WS didn't deliver, fall back to REST
        use_rest_fallback = False
        if not self._live_book.is_ready:
            self._ws_status = "polling"
            use_rest_fallback = True
            self._rest_refresh()

        # Save terminal settings and switch to raw mode for key detection
        old_settings = None
        try:
            old_settings = termios.tcgetattr(sys.stdin)
            tty.setcbreak(sys.stdin.fileno())
        except Exception:
            old_settings = None

        rest_timer = 0.0
        refresh_interval = 0.5  # 2 Hz

        try:
            with Live(
                self._render(),
                console=self.console,
                refresh_per_second=2,
                screen=True,
            ) as live:
                while True:
                    # Key handling
                    key = self._read_key(timeout=refresh_interval)
                    if key:
                        kl = key.lower()
                        if kl == 'q':
                            break
                        elif kl == 'p':
                            self.paused = not self.paused
                        elif kl == 'd':
                            self._depth_idx = (self._depth_idx + 1) % len(self.DEPTH_CHOICES)
                            self.depth = self.DEPTH_CHOICES[self._depth_idx]

                    # REST fallback polling
                    if use_rest_fallback:
                        rest_timer += refresh_interval
                        if rest_timer >= 5.0:
                            rest_timer = 0.0
                            if not self.paused:
                                self._rest_refresh()
                    elif self._ws_status == "connecting" and self._live_book.is_ready:
                        self._ws_status = "connected"

                    # Update display
                    if not self.paused:
                        live.update(self._render())

        except KeyboardInterrupt:
            pass
        finally:
            # Restore terminal
            if old_settings is not None:
                try:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
                except Exception:
                    pass

            # Cleanup WS
            self._stop_event.set()
            ws_thread.join(timeout=3)
            self._analyzer.stop_live_feed()
            self._clob.close()
            self.console.print("[yellow]Live feed stopped[/yellow]")


# ---------------------------------------------------------------------------
# Main TUI entry point
# ---------------------------------------------------------------------------

def _select_market(console: RichConsole) -> Optional[str]:
    """Shared market selection logic. Returns token ID or None."""
    console.print("[bold]Select Market:[/bold]")
    console.print()

    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")

    menu.add_row("1", "Choose from List - Select from active markets")
    menu.add_row("2", "Enter Token ID - Manual token ID entry")
    menu.add_row("", "")
    menu.add_row("b", "Back - Return to main menu")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-2, b):[/cyan] ").strip().lower()
    console.print()

    if choice == '1':
        market = pick_market(
            console,
            prompt="Select a market for order book analysis",
            allow_manual=True,
            limit=15,
        )
        if not market:
            console.print("[yellow]No market selected[/yellow]")
            return None

        clob_ids = market.get('clobTokenIds', [])
        if isinstance(clob_ids, str):
            try:
                import json
                clob_ids = json.loads(clob_ids)
            except Exception:
                clob_ids = []

        market_id = None
        if clob_ids:
            if len(clob_ids) >= 2:
                console.print()
                console.print("[bold]Select outcome:[/bold]")
                console.print("  [cyan]1[/cyan] YES token")
                console.print("  [cyan]2[/cyan] NO token")
                outcome = console.input("[cyan]Choice (1/2):[/cyan] ").strip()
                if outcome == '2' and len(clob_ids) > 1:
                    market_id = clob_ids[1]
                else:
                    market_id = clob_ids[0]
            else:
                market_id = clob_ids[0]
        else:
            market_id = get_market_id(market)

        if not market_id:
            console.print("[red]Could not get token ID for this market[/red]")
            console.print("[dim]Try entering the token ID manually[/dim]")
            market_id = console.input("[cyan]Enter token ID:[/cyan] ").strip()
            if not market_id:
                return None

        return market_id

    elif choice == '2':
        market_id = console.input("[cyan]Enter market token ID:[/cyan] ").strip()
        if not market_id:
            console.print("[red]No ID provided[/red]")
            return None
        return market_id

    elif choice == 'b':
        return None

    else:
        console.print("[red]Invalid option[/red]")
        return None


def orderbook_screen(console: RichConsole):
    """Analyze order book for a market

    Args:
        console: Rich Console instance
    """
    console.print(Panel(
        "[bold]Order Book Analyzer[/bold]\n"
        "[dim]Depth charts, slippage, liquidity analysis[/dim]",
        style="cyan",
    ))
    console.print()

    # Mode selection
    console.print("[bold]Mode:[/bold]")
    console.print()

    mode_menu = Table.grid(padding=(0, 1))
    mode_menu.add_column(style="cyan bold", justify="right", width=3)
    mode_menu.add_column(style="white")

    mode_menu.add_row("1", "Live Order Book - Real-time WebSocket depth display")
    mode_menu.add_row("2", "Static Analysis - One-shot depth chart & slippage")
    mode_menu.add_row("", "")
    mode_menu.add_row("b", "Back - Return to main menu")

    console.print(mode_menu)
    console.print()

    mode = console.input("[cyan]Select mode (1-2, b):[/cyan] ").strip().lower()
    console.print()

    if mode == 'b':
        return

    if mode == '1':
        _live_orderbook(console)
    elif mode == '2':
        _static_orderbook(console)
    else:
        console.print("[red]Invalid option[/red]")


def _live_orderbook(console: RichConsole):
    """Launch the live order book display."""
    market_id = _select_market(console)
    if not market_id:
        return

    # Depth selection
    console.print()
    console.print("[bold]Initial depth levels:[/bold]")
    console.print("  [cyan]1[/cyan] 10 levels")
    console.print("  [cyan]2[/cyan] 20 levels [dim](default)[/dim]")
    console.print("  [cyan]3[/cyan] 50 levels")
    depth_choice = console.input("[cyan]Choice (1-3):[/cyan] ").strip()
    depth_map = {'1': 10, '2': 20, '3': 50}
    depth = depth_map.get(depth_choice, 20)

    # Derive a display title from the token ID
    title = market_id[:30] + "..." if len(market_id) > 30 else market_id

    console.print()
    console.print(f"[cyan]Starting live order book for {title}...[/cyan]")
    console.print("[dim]Controls: [P]ause/resume  [D]epth cycle  [Q]uit[/dim]")
    console.print()

    display = LiveOrderbookDisplay(
        console=console,
        market_id=market_id,
        market_title=title,
        depth=depth,
    )
    display.run()


def _static_orderbook(console: RichConsole):
    """Run the original one-shot order book analysis via CLI subprocess."""
    market_id = _select_market(console)
    if not market_id:
        return

    console.print()
    console.print("[bold]Analysis Options:[/bold]")
    console.print()

    # Depth
    depth = console.input(
        "Order book depth [cyan][default: 20][/cyan] "
    ).strip() or "20"
    try:
        depth = int(depth)
        if depth < 1:
            depth = 20
        elif depth > 100:
            depth = 100
    except ValueError:
        depth = 20

    # Show chart
    show_chart = console.input(
        "Show ASCII depth chart? [cyan](y/n)[/cyan] [default: y] "
    ).strip().lower()
    show_chart = show_chart != 'n'

    # Slippage calculation
    slippage_size = console.input(
        "Calculate slippage for order size (shares)? [cyan][leave blank to skip][/cyan] "
    ).strip()
    slippage = None
    slippage_side = "buy"
    if slippage_size:
        try:
            slippage = float(slippage_size)
            slippage_side = console.input(
                "Order side [cyan](buy/sell)[/cyan] [default: buy] "
            ).strip().lower() or "buy"
            if slippage_side not in ['buy', 'sell']:
                slippage_side = 'buy'
        except ValueError:
            slippage = None

    console.print()
    console.print("[green]Analyzing order book...[/green]")
    console.print()

    # Build and run command
    cmd = [sys.executable, "-m", "polyterm.cli.main", "orderbook", market_id, f"--depth={depth}"]
    if show_chart:
        cmd.append("--chart")
    if slippage:
        cmd.extend([f"--slippage={slippage}", f"--side={slippage_side}"])

    try:
        subprocess.run(cmd, capture_output=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis cancelled.[/yellow]")
    except Exception as e:
        handle_api_error(console, e, "order book")
