"""Orderbook command - order book analysis and visualization"""

import asyncio
import click
import time
import threading
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ...api.clob import CLOBClient
from ...db.database import Database
from ...core.orderbook import OrderBookAnalyzer, LiveOrderBook
from ...utils.json_output import print_json, format_orderbook_json
from ...utils.errors import handle_api_error


def _render_live_panel(live_book: LiveOrderBook, depth: int = 20) -> Panel:
    """Build a Rich panel from a LiveOrderBook snapshot."""
    tob = live_book.get_top_of_book()
    depth_data = live_book.get_depth(levels=depth)

    table = Table(show_header=True, header_style="bold", expand=True)
    table.add_column("Bid Size", justify="right", style="green")
    table.add_column("Bid Price", justify="right", style="green")
    table.add_column("Ask Price", justify="left", style="red")
    table.add_column("Ask Size", justify="left", style="red")

    bids = depth_data["bids"]
    asks = depth_data["asks"]
    rows = max(len(bids), len(asks))

    for i in range(min(rows, depth)):
        bid_price = f"${float(bids[i]['price']):.4f}" if i < len(bids) else ""
        bid_size = f"{float(bids[i]['size']):,.0f}" if i < len(bids) else ""
        ask_price = f"${float(asks[i]['price']):.4f}" if i < len(asks) else ""
        ask_size = f"{float(asks[i]['size']):,.0f}" if i < len(asks) else ""
        table.add_row(bid_size, bid_price, ask_price, ask_size)

    best_bid = f"${tob['best_bid']:.4f}" if tob["best_bid"] is not None else "—"
    best_ask = f"${tob['best_ask']:.4f}" if tob["best_ask"] is not None else "—"
    spread = f"${tob['spread']:.4f}" if tob["spread"] is not None else "—"
    mid = f"${tob['mid_price']:.4f}" if tob["mid_price"] is not None else "—"
    ltp = f"${tob['last_trade_price']:.4f}" if tob["last_trade_price"] is not None else "—"

    subtitle = (
        f"Bid {best_bid} | Ask {best_ask} | Spread {spread} | "
        f"Mid {mid} | LTP {ltp} | "
        f"Msgs {live_book.message_count}"
    )

    return Panel(table, title="[bold cyan]Live Order Book[/bold cyan]", subtitle=subtitle)


def _run_ws_loop(clob_client: CLOBClient, token_ids: list, analyzer: OrderBookAnalyzer, stop_event: threading.Event):
    """Run the async WS event loop in a background thread."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    async def _run():
        await analyzer.start_live_feed(token_ids)
        # listen_orderbook blocks until disconnected or max reconnects
        try:
            await clob_client.listen_orderbook(
                max_reconnects=10,
                message_timeout=60.0,
            )
        except Exception:
            pass

    task = loop.create_task(_run())

    # Poll stop_event so we can shut down cleanly
    async def _wait_for_stop():
        while not stop_event.is_set():
            await asyncio.sleep(0.25)
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
        await clob_client.close_websocket()

    try:
        loop.run_until_complete(_wait_for_stop())
    except Exception:
        pass
    finally:
        loop.close()


@click.command()
@click.argument("market_id")
@click.option("--depth", default=20, help="Order book depth")
@click.option("--chart", is_flag=True, help="Show ASCII depth chart")
@click.option("--live", is_flag=True, help="Live WebSocket feed (updates in real-time)")
@click.option("--refresh", default=1.0, type=float, help="Live refresh interval in seconds")
@click.option("--slippage", default=None, type=float, help="Calculate slippage for order size")
@click.option("--side", type=click.Choice(["buy", "sell"]), default="buy", help="Order side for slippage")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def orderbook(ctx, market_id, depth, chart, live, refresh, slippage, side, output_format):
    """Analyze order book for a market

    MARKET_ID is the market token ID to analyze.
    """

    config = ctx.obj["config"]
    console = Console()

    # Initialize
    clob_client = CLOBClient(rest_endpoint=config.clob_rest_endpoint)
    db = Database()
    analyzer = OrderBookAnalyzer(clob_client)

    try:
        # --- Live mode ---
        if live:
            if output_format != 'json':
                console.print(f"[cyan]Starting live order book for {market_id[:30]}...[/cyan]")
                console.print("[dim]Press Ctrl+C to stop[/dim]\n")

            stop_event = threading.Event()
            ws_thread = threading.Thread(
                target=_run_ws_loop,
                args=(clob_client, [market_id], analyzer, stop_event),
                daemon=True,
            )
            ws_thread.start()

            # Wait for first data (up to 10s)
            live_book = analyzer.get_live_book(market_id)
            waited = 0.0
            while (live_book is None or not live_book.is_ready) and waited < 10.0:
                time.sleep(0.25)
                waited += 0.25
                live_book = analyzer.get_live_book(market_id)

            if live_book is None or not live_book.is_ready:
                stop_event.set()
                ws_thread.join(timeout=5)
                if output_format == 'json':
                    print_json({'success': False, 'error': 'No data received from WebSocket'})
                else:
                    console.print("[red]No data received from WebSocket within 10s[/red]")
                return

            try:
                if output_format == 'json':
                    # Single snapshot in JSON mode
                    snap = live_book.get_snapshot()
                    tob = live_book.get_top_of_book()
                    print_json({
                        'success': True,
                        'mode': 'live',
                        'timestamp': datetime.now().isoformat(),
                        'top_of_book': tob,
                        'bids': snap['bids'][:depth],
                        'asks': snap['asks'][:depth],
                        'message_count': snap['message_count'],
                    })
                else:
                    with Live(
                        _render_live_panel(live_book, depth),
                        console=console,
                        refresh_per_second=1.0 / refresh if refresh > 0 else 1.0,
                    ) as rich_live:
                        while True:
                            time.sleep(refresh)
                            rich_live.update(_render_live_panel(live_book, depth))
            except KeyboardInterrupt:
                if output_format != 'json':
                    console.print("\n[yellow]Live feed stopped[/yellow]")
            finally:
                stop_event.set()
                ws_thread.join(timeout=5)
                analyzer.stop_live_feed()
            return

        # --- Static (REST) mode ---
        if output_format != 'json':
            console.print(f"[cyan]Analyzing order book for {market_id[:30]}...[/cyan]\n")

        # Get analysis
        with console.status("[bold green]Fetching order book data..."):
            analysis = analyzer.analyze(market_id, depth=depth)

        if not analysis:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Could not fetch order book'})
            else:
                console.print("[red]Could not fetch order book data[/red]")
            return

        # Slippage calculation
        slippage_result = None
        if slippage:
            slippage_result = analyzer.calculate_slippage(market_id, side, slippage)

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'analysis': format_orderbook_json(analysis),
            }
            if slippage_result:
                output['slippage'] = slippage_result
            print_json(output)
            return

        # Display analysis
        console.print(Panel(analyzer.format_analysis(analysis), title="Order Book Analysis"))

        # Show chart if requested
        if chart:
            console.print("\n")
            chart_text = analyzer.render_ascii_depth_chart(market_id, depth=depth)
            console.print(Panel(chart_text, title="Depth Chart"))

        # Show slippage if calculated
        if slippage_result:
            console.print(f"\n[bold]Slippage Analysis ({side.upper()} {slippage:,.0f} shares):[/bold]")
            if 'error' in slippage_result:
                console.print(f"  [red]{slippage_result['error']}[/red]")
            else:
                console.print(f"  Best price: ${slippage_result['best_price']:.4f}")
                console.print(f"  Avg price: ${slippage_result['avg_price']:.4f}")
                console.print(f"  Slippage: ${slippage_result['slippage']:.4f} ({slippage_result['slippage_pct']:.2f}%)")
                console.print(f"  Total cost: ${slippage_result['total_cost']:,.2f}")
                console.print(f"  Price levels used: {slippage_result['levels_used']}")

        # Check for icebergs
        icebergs = analyzer.detect_iceberg_orders(market_id)
        if icebergs:
            console.print(f"\n[yellow]Potential iceberg orders detected: {len(icebergs)}[/yellow]")
            for iceberg in icebergs[:3]:
                console.print(f"  {iceberg['side'].upper()}: {iceberg['size']:,.0f} shares @ multiple prices")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            handle_api_error(console, e, "order book")
    finally:
        clob_client.close()
