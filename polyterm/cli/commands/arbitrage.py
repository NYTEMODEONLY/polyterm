"""Arbitrage command - scan for arbitrage opportunities"""

import asyncio
import json
import sys
import threading
import time

import click
from datetime import datetime
from rich.console import Console
from rich.live import Live
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...db.database import Database
from ...core.arbitrage import ArbitrageScanner, KalshiArbitrageScanner
from ...core.orderbook import OrderBookAnalyzer, LiveOrderBook
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error, show_error


def _build_table(opportunities, min_spread, live=False):
    """Build a Rich table from arb opportunities."""
    title = f"{'[LIVE] ' if live else ''}Arbitrage Opportunities (Spread >= {min_spread:.1%})"
    table = Table(title=title)

    table.add_column("Type", style="cyan")
    table.add_column("Market(s)", style="green", max_width=40)
    table.add_column("Spread", justify="right", style="yellow")
    table.add_column("Profit ($100)", justify="right", style="bold green")
    table.add_column("Confidence", justify="center")

    for opp in opportunities:
        type_display = opp.type.replace('_', ' ').title()

        if opp.type == 'intra_market':
            market_display = opp.market1_title[:40]
        else:
            market_display = f"{opp.market1_title[:18]}... vs {opp.market2_title[:18]}..."

        confidence_style = "green" if opp.confidence == 'high' else "yellow" if opp.confidence == 'medium' else "dim"

        table.add_row(
            type_display,
            market_display,
            f"{opp.spread:.1%}",
            f"${opp.net_profit:.2f}",
            f"[{confidence_style}]{opp.confidence}[/{confidence_style}]",
        )

    return table


def _collect_token_ids(markets):
    """Extract all CLOB token IDs from Gamma markets for WS subscription."""
    token_ids = []
    for event in markets:
        for market in event.get('markets', []):
            raw = market.get('clobTokenIds', [])
            if isinstance(raw, str):
                try:
                    raw = json.loads(raw)
                except Exception:
                    raw = []
            for tid in (raw or []):
                token_ids.append(str(tid))
    return token_ids


def _run_live_mode(config, console, min_spread, limit, include_kalshi, output_format):
    """Run the arb scanner in live mode with WS price feeds."""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
    )
    db = Database()
    analyzer = OrderBookAnalyzer(clob_client)
    stop_event = threading.Event()

    try:
        # Fetch markets once for structure
        if output_format != 'json':
            console.print("[cyan]Fetching markets for live arb scanning...[/cyan]")
        markets = gamma_client.get_markets(limit=100, active=True, closed=False)

        if not markets:
            show_error(console, "no_markets")
            return

        # Collect all token IDs for WS subscription
        token_ids = _collect_token_ids(markets)
        if not token_ids:
            if output_format != 'json':
                console.print("[yellow]No CLOB token IDs found in markets, falling back to REST mode.[/yellow]")
            return

        # Start WS feed in background thread
        def _ws_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            async def _run():
                await analyzer.start_live_feed(token_ids)
                try:
                    await clob_client.listen_orderbook(
                        max_reconnects=10,
                        message_timeout=60.0,
                    )
                except Exception:
                    pass

            task = loop.create_task(_run())

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

        ws_thread = threading.Thread(target=_ws_thread, daemon=True)
        ws_thread.start()

        # Wait for WS to connect and deliver initial data
        if output_format != 'json':
            console.print("[cyan]Connecting to live order book feeds...[/cyan]")
        waited = 0.0
        while waited < 8.0:
            live_data = analyzer.get_live_prices(token_ids[:4])
            if live_data:
                break
            time.sleep(0.5)
            waited += 0.5

        has_live = bool(analyzer.get_live_prices(token_ids[:4]))
        if output_format != 'json':
            if has_live:
                console.print("[green]Live feed connected. Press Ctrl+C to stop.[/green]\n")
            else:
                console.print("[yellow]WS feed not ready, using REST prices with live fallback.[/yellow]\n")

        # Create scanner with live analyzer
        scanner = ArbitrageScanner(
            database=db,
            gamma_client=gamma_client,
            clob_client=clob_client,
            min_spread=min_spread,
            orderbook_analyzer=analyzer,
        )

        scan_interval = 3.0  # seconds between scans
        scan_count = 0

        try:
            with Live(console=console, refresh_per_second=1, screen=True) as live_display:
                while True:
                    scan_count += 1
                    all_opps = []
                    all_opps.extend(scanner.scan_intra_market_arbitrage(markets))
                    all_opps.extend(scanner.scan_correlated_markets(markets))
                    all_opps.sort(key=lambda x: x.net_profit, reverse=True)
                    all_opps = all_opps[:limit]

                    if output_format == 'json':
                        output = {
                            'success': True,
                            'timestamp': datetime.now().isoformat(),
                            'scan': scan_count,
                            'live': has_live,
                            'min_spread': min_spread,
                            'count': len(all_opps),
                            'opportunities': [
                                {
                                    'type': o.type,
                                    'market1_id': o.market1_id,
                                    'market2_id': o.market2_id,
                                    'market1_title': o.market1_title,
                                    'market2_title': o.market2_title,
                                    'spread': o.spread,
                                    'spread_pct': o.spread * 100,
                                    'expected_profit_usd': o.net_profit,
                                    'confidence': o.confidence,
                                }
                                for o in all_opps
                            ],
                        }
                        print_json(output)
                    else:
                        live_prices_count = len(analyzer.get_live_prices(token_ids))
                        table = _build_table(all_opps, min_spread, live=True)

                        from rich.text import Text
                        from rich.panel import Panel
                        from rich.columns import Columns

                        status_text = Text()
                        status_text.append(f"Scan #{scan_count}", style="bold")
                        status_text.append(f" | {datetime.now().strftime('%H:%M:%S')}")
                        status_text.append(f" | Live feeds: {live_prices_count}/{len(token_ids)}")
                        status_text.append(f" | Opps: {len(all_opps)}")
                        if all_opps:
                            total = sum(o.net_profit for o in all_opps)
                            status_text.append(f" | Total: ${total:.2f}")
                        status_text.append(" | Press Ctrl+C to stop", style="dim")

                        from rich.console import Group
                        live_display.update(Group(status_text, table) if all_opps else Group(status_text, Text("No opportunities found", style="dim")))

                    time.sleep(scan_interval)

        except KeyboardInterrupt:
            if output_format != 'json':
                console.print("\n[cyan]Stopping live arb scanner...[/cyan]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            handle_api_error(console, e, "live arbitrage scanning")
    finally:
        stop_event.set()
        if 'ws_thread' in dir() and ws_thread.is_alive():
            ws_thread.join(timeout=3)
        analyzer.stop_live_feed()
        gamma_client.close()
        clob_client.close()


@click.command()
@click.option("--min-spread", default=0.025, help="Minimum spread for arbitrage (default: 2.5%)")
@click.option("--limit", default=10, help="Maximum opportunities to show")
@click.option("--include-kalshi", is_flag=True, help="Include Kalshi cross-platform arbitrage")
@click.option("--live", is_flag=True, help="Live mode: stream arb opportunities using WebSocket price data")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def arbitrage(ctx, min_spread, limit, include_kalshi, live, output_format):
    """Scan for arbitrage opportunities across markets"""

    config = ctx.obj["config"]
    console = Console()

    if live:
        _run_live_mode(config, console, min_spread, limit, include_kalshi, output_format)
        return

    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
    )
    db = Database()

    try:
        # Initialize scanner
        scanner = ArbitrageScanner(
            database=db,
            gamma_client=gamma_client,
            clob_client=clob_client,
            min_spread=min_spread,
        )

        if output_format != 'json':
            console.print(f"[cyan]Scanning for arbitrage opportunities (min spread: {min_spread:.1%})...[/cyan]\n")

        # Get markets
        with console.status("[bold green]Fetching markets for arbitrage scan...") as status:
            markets = gamma_client.get_markets(limit=100, active=True, closed=False)

            # Scan for opportunities
            all_opportunities = []

            # Intra-market arbitrage
            status.update("[bold green]Scanning intra-market arbitrage...")
            intra_opps = scanner.scan_intra_market_arbitrage(markets)
            all_opportunities.extend(intra_opps)

            # Correlated market arbitrage
            status.update("[bold green]Scanning correlated markets...")
            correlated_opps = scanner.scan_correlated_markets(markets)
            all_opportunities.extend(correlated_opps)

        # Kalshi cross-platform (if enabled and configured)
        if include_kalshi and config.kalshi_api_key:
            kalshi_scanner = KalshiArbitrageScanner(
                database=db,
                gamma_client=gamma_client,
                kalshi_api_key=config.kalshi_api_key,
            )
            kalshi_opps = kalshi_scanner.scan_cross_platform_arbitrage(min_spread)
            all_opportunities.extend(kalshi_opps)

        # Sort by profit
        all_opportunities.sort(key=lambda x: x.net_profit, reverse=True)
        all_opportunities = all_opportunities[:limit]

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'min_spread': min_spread,
                'count': len(all_opportunities),
                'opportunities': [
                    {
                        'type': opp.type,
                        'market1_id': opp.market1_id,
                        'market2_id': opp.market2_id,
                        'market1_title': opp.market1_title,
                        'market2_title': opp.market2_title,
                        'spread': opp.spread,
                        'spread_pct': opp.spread * 100,
                        'expected_profit_usd': opp.net_profit,
                        'confidence': opp.confidence,
                    }
                    for opp in all_opportunities
                ],
            }
            print_json(output)
            return

        if not all_opportunities:
            show_error(console, "no_arbitrage")
            return

        # Create table
        table = _build_table(all_opportunities, min_spread)
        console.print(table)

        # Summary
        total_potential = sum(opp.net_profit for opp in all_opportunities)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Opportunities found: {len(all_opportunities)}")
        console.print(f"  Total potential profit (per $100): ${total_potential:.2f}")

        if not include_kalshi:
            console.print(f"\n[dim]Tip: Use --include-kalshi to scan cross-platform opportunities[/dim]")
        console.print(f"[dim]Tip: Use --live for real-time WebSocket-fed arb scanning[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            handle_api_error(console, e, "scanning for arbitrage")
    finally:
        gamma_client.close()
        clob_client.close()
