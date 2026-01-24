"""15-Minute Crypto Markets - Monitor and trade short-term crypto prediction markets"""

import click
import time
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error


# 15-minute crypto market identifiers
CRYPTO_15M_MARKETS = {
    'BTC': {
        'name': 'Bitcoin',
        'symbol': 'BTC',
        'search_terms': ['bitcoin 15m', 'btc 15 minute', 'bitcoin price'],
        'color': 'yellow',
    },
    'ETH': {
        'name': 'Ethereum',
        'symbol': 'ETH',
        'search_terms': ['ethereum 15m', 'eth 15 minute', 'ethereum price'],
        'color': 'cyan',
    },
    'SOL': {
        'name': 'Solana',
        'symbol': 'SOL',
        'search_terms': ['solana 15m', 'sol 15 minute', 'solana price'],
        'color': 'magenta',
    },
    'XRP': {
        'name': 'XRP',
        'symbol': 'XRP',
        'search_terms': ['xrp 15m', 'xrp 15 minute', 'xrp price'],
        'color': 'blue',
    },
}


def search_markets_fallback(gamma_client: GammaClient, query: str, limit: int = 10) -> list:
    """Search markets with fallback to filtering get_markets results"""
    # Try search endpoint first
    try:
        results = gamma_client.search_markets(query, limit=limit)
        if results:
            return results
    except Exception:
        pass

    # Fallback: get all markets and filter locally
    try:
        markets = gamma_client.get_markets(limit=200)
        query_lower = query.lower()

        matches = []
        for market in markets:
            title = market.get('question', market.get('title', '')).lower()
            if query_lower in title:
                matches.append(market)
                if len(matches) >= limit:
                    break

        return matches
    except Exception:
        return []


def find_15m_markets(gamma_client: GammaClient, crypto: str = None) -> list:
    """Find active 15-minute crypto markets"""
    markets = []

    # First, try to get all markets and filter for 15M crypto
    try:
        all_markets = gamma_client.get_markets(limit=300)
        for market in all_markets:
            title = market.get('question', market.get('title', '')).lower()

            # Check if this is a 15-minute market
            if '15' in title and ('minute' in title or 'min' in title or '15m' in title):
                # Check which crypto it is
                for symbol, info in CRYPTO_15M_MARKETS.items():
                    if crypto and symbol != crypto.upper():
                        continue
                    if any(s.lower() in title for s in [symbol.lower(), info['name'].lower()]):
                        market_id = market.get('id', market.get('condition_id', ''))
                        if market_id and not any(m.get('id') == market_id for m in markets):
                            market['crypto_symbol'] = symbol
                            market['crypto_name'] = info['name']
                            markets.append(market)
                            break
    except Exception:
        pass

    # If no markets found via get_markets, try search
    if not markets:
        cryptos_to_search = [crypto.upper()] if crypto else CRYPTO_15M_MARKETS.keys()

        for symbol in cryptos_to_search:
            if symbol not in CRYPTO_15M_MARKETS:
                continue

            info = CRYPTO_15M_MARKETS[symbol]

            for term in info['search_terms']:
                try:
                    results = search_markets_fallback(gamma_client, term, limit=10)
                    for market in results:
                        title = market.get('question', market.get('title', '')).lower()
                        # Filter for 15-minute markets
                        if '15' in title and ('minute' in title or 'min' in title or '15m' in title):
                            if any(s.lower() in title for s in [symbol, info['name'].lower()]):
                                market_id = market.get('id', market.get('condition_id', ''))
                                if market_id and not any(m.get('id') == market_id for m in markets):
                                    market['crypto_symbol'] = symbol
                                    market['crypto_name'] = info['name']
                                    markets.append(market)
                except Exception:
                    continue

    return markets


def get_market_probability(market: dict) -> tuple:
    """Extract YES/NO probabilities from market"""
    outcome_prices = market.get('outcomePrices')
    if not outcome_prices and market.get('markets') and len(market.get('markets', [])) > 0:
        outcome_prices = market['markets'][0].get('outcomePrices')

    if isinstance(outcome_prices, str):
        import json
        try:
            outcome_prices = json.loads(outcome_prices)
        except Exception:
            return 0.5, 0.5

    if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
        return float(outcome_prices[0]), float(outcome_prices[1])
    elif outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) == 1:
        yes_price = float(outcome_prices[0])
        return yes_price, 1 - yes_price

    return 0.5, 0.5


def format_time_remaining(end_date_str: str) -> str:
    """Format time remaining until market resolution"""
    if not end_date_str:
        return "?"

    try:
        from dateutil import parser
        end_date = parser.parse(end_date_str)
    except ImportError:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        except Exception:
            return "?"
    except Exception:
        return "?"

    now = datetime.now(timezone.utc)
    remaining = end_date - now

    if remaining.total_seconds() <= 0:
        return "[red]ENDED[/red]"

    minutes = int(remaining.total_seconds() / 60)
    seconds = int(remaining.total_seconds() % 60)

    if minutes > 0:
        return f"{minutes}m {seconds}s"
    else:
        return f"[yellow]{seconds}s[/yellow]"


@click.command()
@click.option("--crypto", "-c", type=click.Choice(["BTC", "ETH", "SOL", "XRP", "all"], case_sensitive=False),
              default="all", help="Cryptocurrency to monitor")
@click.option("--refresh", "-r", default=5, help="Refresh interval in seconds")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode with trade analysis")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.option("--once", is_flag=True, help="Run once and exit (no live updates)")
@click.pass_context
def crypto15m(ctx, crypto, refresh, interactive, output_format, once):
    """Monitor 15-minute crypto prediction markets (BTC, ETH, SOL, XRP)

    These markets resolve every 15 minutes based on whether the crypto price
    goes UP or DOWN. Resolution uses Chainlink price feeds.

    Examples:
        polyterm crypto15m                    # Monitor all 15M crypto markets
        polyterm crypto15m -c BTC             # Monitor Bitcoin 15M only
        polyterm crypto15m -c ETH --refresh 3 # Ethereum with 3s refresh
        polyterm crypto15m -i                 # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )

    crypto_filter = None if crypto.lower() == "all" else crypto.upper()

    def generate_display():
        """Generate the market display"""
        now = datetime.now()

        # Main table
        table = Table(
            title=f"15-Minute Crypto Markets (Updated: {now.strftime('%H:%M:%S')})",
            title_style="bold cyan",
        )

        table.add_column("Crypto", style="bold", width=8)
        table.add_column("Market", style="cyan", max_width=35)
        table.add_column("UP", justify="center", width=10)
        table.add_column("DOWN", justify="center", width=10)
        table.add_column("Volume", justify="right", width=12)
        table.add_column("Liquidity", justify="right", width=12)
        table.add_column("Ends In", justify="right", width=10)

        try:
            markets = find_15m_markets(gamma_client, crypto_filter)

            if not markets:
                table.add_row(
                    "[dim]No active 15M markets found[/dim]",
                    "", "", "", "", "", ""
                )
            else:
                for market in markets:
                    symbol = market.get('crypto_symbol', '?')
                    info = CRYPTO_15M_MARKETS.get(symbol, {'color': 'white'})

                    title = market.get('question', market.get('title', ''))[:35]

                    yes_prob, no_prob = get_market_probability(market)

                    # Color code based on probability
                    up_color = "green" if yes_prob > 0.5 else "white"
                    down_color = "red" if no_prob > 0.5 else "white"

                    volume = float(market.get('volume24hr', market.get('volume', 0)) or 0)
                    liquidity = float(market.get('liquidity', 0) or 0)

                    time_remaining = format_time_remaining(market.get('endDate', ''))

                    table.add_row(
                        f"[{info['color']}]{symbol}[/{info['color']}]",
                        title,
                        f"[{up_color}]{yes_prob:.0%}[/{up_color}]",
                        f"[{down_color}]{no_prob:.0%}[/{down_color}]",
                        f"${volume:,.0f}",
                        f"${liquidity:,.0f}",
                        time_remaining,
                    )

        except Exception as e:
            handle_api_error(console, e, "fetching 15M markets")

        return table

    def get_markets_json():
        """Get markets data as JSON"""
        try:
            markets = find_15m_markets(gamma_client, crypto_filter)
            return {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'count': len(markets),
                'markets': [
                    {
                        'id': m.get('id', m.get('condition_id', '')),
                        'title': m.get('question', m.get('title', '')),
                        'crypto': m.get('crypto_symbol', ''),
                        'crypto_name': m.get('crypto_name', ''),
                        'up_probability': get_market_probability(m)[0],
                        'down_probability': get_market_probability(m)[1],
                        'volume': float(m.get('volume24hr', m.get('volume', 0)) or 0),
                        'liquidity': float(m.get('liquidity', 0) or 0),
                        'end_date': m.get('endDate', ''),
                        'active': m.get('active', False),
                        'closed': m.get('closed', False),
                    }
                    for m in markets
                ],
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # Interactive mode
    if interactive:
        console.print()
        console.print(Panel(
            "[bold cyan]15-Minute Crypto Markets[/bold cyan]\n\n"
            "Trade short-term crypto price predictions.\n"
            "Markets resolve every 15 minutes using Chainlink oracles.\n\n"
            "[dim]UP = price at end >= price at start[/dim]\n"
            "[dim]DOWN = price at end < price at start[/dim]",
            border_style="cyan"
        ))
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Finding 15M markets...", total=None)
            markets = find_15m_markets(gamma_client, crypto_filter)

        if not markets:
            console.print("[yellow]No active 15-minute markets found.[/yellow]")
            console.print("[dim]Try again in a few minutes - new markets open every 15 minutes.[/dim]")
            gamma_client.close()
            clob_client.close()
            return

        # Display markets
        console.print(generate_display())
        console.print()

        # Interactive selection
        console.print("[bold]Available Actions:[/bold]")
        console.print("  [cyan]1[/cyan] - Analyze a market for trading")
        console.print("  [cyan]2[/cyan] - View order book depth")
        console.print("  [cyan]3[/cyan] - Refresh markets")
        console.print("  [cyan]q[/cyan] - Quit")
        console.print()

        while True:
            choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "q"], default="q")

            if choice == "q":
                break
            elif choice == "3":
                console.print(generate_display())
                console.print()
            elif choice in ["1", "2"]:
                # Select market
                console.print()
                for i, m in enumerate(markets, 1):
                    symbol = m.get('crypto_symbol', '?')
                    title = m.get('question', m.get('title', ''))[:40]
                    yes_prob, _ = get_market_probability(m)
                    console.print(f"  [{i}] {symbol}: {title} (UP: {yes_prob:.0%})")

                console.print()
                market_idx = Prompt.ask("Select market number", default="1")

                try:
                    idx = int(market_idx) - 1
                    if 0 <= idx < len(markets):
                        selected = markets[idx]

                        if choice == "1":
                            # Trade analysis
                            _display_trade_analysis(console, selected, clob_client)
                        elif choice == "2":
                            # Order book
                            _display_order_book(console, selected, clob_client)
                except (ValueError, IndexError):
                    console.print("[yellow]Invalid selection[/yellow]")

        gamma_client.close()
        clob_client.close()
        return

    # JSON output mode
    if output_format == 'json':
        print_json(get_markets_json())
        gamma_client.close()
        clob_client.close()
        return

    # Run once mode
    if once:
        console.print(generate_display())
        gamma_client.close()
        clob_client.close()
        return

    # Live display mode
    try:
        with Live(generate_display(), refresh_per_second=1/refresh, console=console) as live:
            while True:
                time.sleep(refresh)
                live.update(generate_display())

    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")
    finally:
        gamma_client.close()
        clob_client.close()


def _display_trade_analysis(console: Console, market: dict, clob_client: CLOBClient):
    """Display trade analysis for a 15M market"""
    console.print()

    title = market.get('question', market.get('title', ''))
    symbol = market.get('crypto_symbol', '?')
    yes_prob, no_prob = get_market_probability(market)
    volume = float(market.get('volume24hr', market.get('volume', 0)) or 0)
    liquidity = float(market.get('liquidity', 0) or 0)

    console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
    console.print()

    # Current prices
    table = Table(show_header=False, box=None)
    table.add_column(width=20)
    table.add_column(width=15, justify="right")

    table.add_row("[bold]Current Prices:[/bold]", "")
    table.add_row("  UP (YES)", f"[green]{yes_prob:.2f}[/green] ({yes_prob:.0%})")
    table.add_row("  DOWN (NO)", f"[red]{no_prob:.2f}[/red] ({no_prob:.0%})")
    table.add_row("", "")
    table.add_row("[bold]Market Stats:[/bold]", "")
    table.add_row("  24h Volume", f"${volume:,.0f}")
    table.add_row("  Liquidity", f"${liquidity:,.0f}")
    table.add_row("  Time Left", format_time_remaining(market.get('endDate', '')))

    console.print(table)
    console.print()

    # Trade scenarios
    console.print("[bold]Trade Scenarios ($100 position):[/bold]")
    console.print()

    scenarios_table = Table(show_header=True, header_style="bold")
    scenarios_table.add_column("Side", width=10)
    scenarios_table.add_column("Entry", width=10, justify="right")
    scenarios_table.add_column("Shares", width=10, justify="right")
    scenarios_table.add_column("If Win", width=12, justify="right")
    scenarios_table.add_column("If Lose", width=12, justify="right")
    scenarios_table.add_column("ROI", width=10, justify="right")

    amount = 100

    # UP scenario
    up_shares = amount / yes_prob if yes_prob > 0 else 0
    up_win = up_shares - amount
    up_lose = -amount
    up_roi = (up_win / amount) * 100 if amount > 0 else 0

    scenarios_table.add_row(
        "[green]UP[/green]",
        f"${yes_prob:.2f}",
        f"{up_shares:.1f}",
        f"[green]+${up_win:.2f}[/green]",
        f"[red]-${amount:.2f}[/red]",
        f"[green]+{up_roi:.0f}%[/green]",
    )

    # DOWN scenario
    down_shares = amount / no_prob if no_prob > 0 else 0
    down_win = down_shares - amount
    down_lose = -amount
    down_roi = (down_win / amount) * 100 if amount > 0 else 0

    scenarios_table.add_row(
        "[red]DOWN[/red]",
        f"${no_prob:.2f}",
        f"{down_shares:.1f}",
        f"[green]+${down_win:.2f}[/green]",
        f"[red]-${amount:.2f}[/red]",
        f"[green]+{down_roi:.0f}%[/green]",
    )

    console.print(scenarios_table)
    console.print()

    # Risk warning
    console.print("[dim]Note: 15M markets are high-risk due to short timeframes and crypto volatility.[/dim]")
    console.print("[dim]Always size positions appropriately and never risk more than you can afford to lose.[/dim]")
    console.print()

    # Trade link
    market_id = market.get('id', market.get('condition_id', ''))
    if market_id:
        console.print(f"[bold]Trade on Polymarket:[/bold]")
        console.print(f"  https://polymarket.com/event/{market_id}")
    console.print()


def _display_order_book(console: Console, market: dict, clob_client: CLOBClient):
    """Display order book for a 15M market"""
    console.print()

    title = market.get('question', market.get('title', ''))

    console.print(Panel(f"[bold]Order Book: {title[:50]}[/bold]", border_style="cyan"))
    console.print()

    # Get CLOB token ID
    clob_tokens = market.get('clobTokenIds', [])
    if not clob_tokens:
        console.print("[yellow]Order book data not available for this market[/yellow]")
        return

    try:
        orderbook = clob_client.get_order_book(clob_tokens[0], depth=10)

        if not orderbook:
            console.print("[yellow]No order book data available[/yellow]")
            return

        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        # Create side-by-side table
        table = Table(show_header=True, header_style="bold")
        table.add_column("Bid Price", justify="right", style="green", width=12)
        table.add_column("Bid Size", justify="right", width=12)
        table.add_column("Ask Price", justify="right", style="red", width=12)
        table.add_column("Ask Size", justify="right", width=12)

        max_rows = max(len(bids), len(asks))

        for i in range(min(max_rows, 10)):
            bid_price = ""
            bid_size = ""
            ask_price = ""
            ask_size = ""

            if i < len(bids):
                bid = bids[i]
                if isinstance(bid, dict):
                    bid_price = f"${float(bid.get('price', 0)):.3f}"
                    bid_size = f"{float(bid.get('size', 0)):,.0f}"

            if i < len(asks):
                ask = asks[i]
                if isinstance(ask, dict):
                    ask_price = f"${float(ask.get('price', 0)):.3f}"
                    ask_size = f"{float(ask.get('size', 0)):,.0f}"

            table.add_row(bid_price, bid_size, ask_price, ask_size)

        console.print(table)

        # Spread calculation
        if bids and asks:
            spread = clob_client.calculate_spread(orderbook)
            console.print()
            console.print(f"[bold]Spread:[/bold] {spread:.2f}%")

    except Exception as e:
        console.print(f"[red]Error fetching order book: {e}[/red]")

    console.print()
