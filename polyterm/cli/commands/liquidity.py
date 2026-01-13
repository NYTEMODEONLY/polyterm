"""Liquidity Command - Cross-market liquidity comparison"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


@click.command()
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--min-volume", "-v", type=float, default=1000, help="Minimum 24h volume")
@click.option("--limit", "-l", type=int, default=20, help="Number of markets to compare")
@click.option("--sort", "-s", type=click.Choice(["liquidity", "spread", "depth", "score"]),
              default="score", help="Sort by metric")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def liquidity(ctx, category, min_volume, limit, sort, output_format):
    """Compare liquidity across markets

    Find the most liquid markets for easier trading with
    lower slippage and better execution.

    Metrics:
        liquidity - Total order book depth
        spread    - Bid-ask spread (lower is better)
        depth     - Combined bid/ask size
        score     - Composite liquidity score

    Examples:
        polyterm liquidity                    # Top liquid markets
        polyterm liquidity -c "crypto"        # Crypto markets only
        polyterm liquidity -s spread          # Sort by tightest spread
        polyterm liquidity -v 10000           # High volume only
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        base_url=config.clob_base_url,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("Analyzing liquidity...", total=None)

            # Get markets
            markets = gamma_client.get_markets(limit=200)

            # Filter by category if specified
            if category:
                markets = [
                    m for m in markets
                    if category.lower() in (m.get('category', '') or '').lower()
                    or any(category.lower() in (t or '').lower() for t in (m.get('tags', []) or []))
                ]

            # Filter by volume
            markets = [
                m for m in markets
                if float(m.get('volume24hr', 0) or 0) >= min_volume
            ]

            # Analyze each market
            liquidity_data = []

            for i, market in enumerate(markets[:limit * 2]):  # Get extra in case some fail
                if len(liquidity_data) >= limit:
                    break

                progress.update(task, description=f"Analyzing market {i + 1}...")

                market_id = market.get('id', market.get('condition_id', ''))
                title = market.get('question', market.get('title', ''))[:45]

                # Get CLOB token
                clob_token = market.get('clobTokenIds', [''])[0] if market.get('clobTokenIds') else ''

                if not clob_token:
                    continue

                # Get order book
                try:
                    orderbook = clob_client.get_orderbook(clob_token)
                except:
                    continue

                if not orderbook:
                    continue

                bids = orderbook.get('bids', [])
                asks = orderbook.get('asks', [])

                if not bids or not asks:
                    continue

                # Calculate metrics
                analysis = _analyze_liquidity(bids, asks, market)

                if analysis['spread'] > 0.50:  # Skip very illiquid markets
                    continue

                analysis['id'] = market_id
                analysis['title'] = title
                analysis['volume_24h'] = float(market.get('volume24hr', 0) or 0)
                analysis['category'] = market.get('category', '')

                liquidity_data.append(analysis)

        # Sort results
        sort_keys = {
            'liquidity': lambda x: x['total_liquidity'],
            'spread': lambda x: -x['spread'],  # Lower is better, so negate
            'depth': lambda x: x['total_depth'],
            'score': lambda x: x['liquidity_score'],
        }
        liquidity_data.sort(key=sort_keys.get(sort, lambda x: x['liquidity_score']), reverse=True)
        liquidity_data = liquidity_data[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'filters': {
                    'category': category,
                    'min_volume': min_volume,
                },
                'sort': sort,
                'markets': liquidity_data,
            })
            return

        # Display results
        console.print()
        console.print(Panel("[bold]Liquidity Comparison[/bold]", border_style="cyan"))
        console.print()

        if category:
            console.print(f"[dim]Category: {category} | Min Volume: ${min_volume:,.0f} | Sorted by: {sort}[/dim]")
            console.print()

        if not liquidity_data:
            console.print("[yellow]No markets found matching criteria.[/yellow]")
            return

        # Main table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("#", width=3, justify="right")
        table.add_column("Market", width=35)
        table.add_column("Spread", width=8, justify="center")
        table.add_column("Bid Depth", width=12, justify="right")
        table.add_column("Ask Depth", width=12, justify="right")
        table.add_column("Score", width=8, justify="center")
        table.add_column("Rating", width=10, justify="center")

        for i, m in enumerate(liquidity_data, 1):
            # Color code spread
            spread = m['spread']
            if spread < 0.02:
                spread_str = f"[green]{spread:.1%}[/green]"
            elif spread < 0.05:
                spread_str = f"[yellow]{spread:.1%}[/yellow]"
            else:
                spread_str = f"[red]{spread:.1%}[/red]"

            # Rating
            score = m['liquidity_score']
            if score >= 80:
                rating = "[green]Excellent[/green]"
            elif score >= 60:
                rating = "[bright_green]Good[/bright_green]"
            elif score >= 40:
                rating = "[yellow]Fair[/yellow]"
            else:
                rating = "[red]Poor[/red]"

            table.add_row(
                str(i),
                m['title'],
                spread_str,
                f"${m['bid_depth']:,.0f}",
                f"${m['ask_depth']:,.0f}",
                f"{score}/100",
                rating,
            )

        console.print(table)
        console.print()

        # Summary stats
        if liquidity_data:
            avg_spread = sum(m['spread'] for m in liquidity_data) / len(liquidity_data)
            avg_score = sum(m['liquidity_score'] for m in liquidity_data) / len(liquidity_data)
            total_liq = sum(m['total_liquidity'] for m in liquidity_data)

            console.print("[bold]Summary:[/bold]")
            console.print(f"  Markets Analyzed: {len(liquidity_data)}")
            console.print(f"  Average Spread: {avg_spread:.2%}")
            console.print(f"  Average Score: {avg_score:.0f}/100")
            console.print(f"  Total Liquidity: ${total_liq:,.0f}")
            console.print()

        # Trading tips
        console.print("[bold]Liquidity Tips:[/bold]")
        console.print()
        console.print("  [cyan]Spread < 2%[/cyan]   - Excellent for market orders")
        console.print("  [cyan]Spread 2-5%[/cyan]  - Use limit orders for better fills")
        console.print("  [cyan]Spread > 5%[/cyan]  - Consider the cost carefully")
        console.print()

        # Top picks
        if liquidity_data:
            best = liquidity_data[0]
            console.print(f"[green]Best Liquidity:[/green] {best['title']}")
            console.print(f"  Spread: {best['spread']:.2%} | Score: {best['liquidity_score']}/100")
            console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()


def _analyze_liquidity(bids: list, asks: list, market: dict) -> dict:
    """Analyze market liquidity"""
    # Parse orders
    parsed_bids = []
    for bid in bids:
        try:
            price = float(bid.get('price', 0))
            size = float(bid.get('size', 0))
            if price > 0 and size > 0:
                parsed_bids.append({'price': price, 'size': size, 'value': price * size})
        except (ValueError, TypeError):
            continue

    parsed_asks = []
    for ask in asks:
        try:
            price = float(ask.get('price', 0))
            size = float(ask.get('size', 0))
            if price > 0 and size > 0:
                parsed_asks.append({'price': price, 'size': size, 'value': price * size})
        except (ValueError, TypeError):
            continue

    # Sort
    parsed_bids.sort(key=lambda x: x['price'], reverse=True)
    parsed_asks.sort(key=lambda x: x['price'])

    # Calculate metrics
    best_bid = parsed_bids[0]['price'] if parsed_bids else 0
    best_ask = parsed_asks[0]['price'] if parsed_asks else 1

    spread = best_ask - best_bid if best_bid > 0 else 1
    mid_price = (best_bid + best_ask) / 2 if best_bid > 0 else 0.5

    bid_depth = sum(b['value'] for b in parsed_bids)
    ask_depth = sum(a['value'] for a in parsed_asks)
    total_depth = bid_depth + ask_depth

    # Market liquidity from API
    market_liquidity = float(market.get('liquidity', 0) or 0)
    total_liquidity = max(total_depth, market_liquidity)

    # Calculate liquidity score (0-100)
    score = 0

    # Spread component (40 points max)
    if spread < 0.01:
        score += 40
    elif spread < 0.02:
        score += 35
    elif spread < 0.03:
        score += 30
    elif spread < 0.05:
        score += 20
    elif spread < 0.10:
        score += 10

    # Depth component (30 points max)
    if total_depth > 100000:
        score += 30
    elif total_depth > 50000:
        score += 25
    elif total_depth > 10000:
        score += 20
    elif total_depth > 5000:
        score += 15
    elif total_depth > 1000:
        score += 10
    elif total_depth > 100:
        score += 5

    # Balance component (15 points max)
    if bid_depth > 0 and ask_depth > 0:
        ratio = min(bid_depth, ask_depth) / max(bid_depth, ask_depth)
        if ratio > 0.8:
            score += 15
        elif ratio > 0.5:
            score += 10
        elif ratio > 0.3:
            score += 5

    # Level count component (15 points max)
    bid_levels = len(set(b['price'] for b in parsed_bids))
    ask_levels = len(set(a['price'] for a in parsed_asks))
    total_levels = bid_levels + ask_levels

    if total_levels > 20:
        score += 15
    elif total_levels > 10:
        score += 10
    elif total_levels > 5:
        score += 5

    return {
        'best_bid': best_bid,
        'best_ask': best_ask,
        'spread': spread,
        'spread_pct': spread / mid_price if mid_price > 0 else 1,
        'mid_price': mid_price,
        'bid_depth': bid_depth,
        'ask_depth': ask_depth,
        'total_depth': total_depth,
        'total_liquidity': total_liquidity,
        'bid_levels': bid_levels,
        'ask_levels': ask_levels,
        'liquidity_score': min(100, score),
    }
