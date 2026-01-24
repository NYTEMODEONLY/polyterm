"""Timing Analysis - Find optimal times to trade"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=True)
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def timing(ctx, market_search, output_format):
    """Analyze optimal timing for trading a market

    Combines spread, volume, and momentum analysis to suggest
    the best times and conditions for entry/exit.

    Examples:
        polyterm timing "bitcoin"    # Full timing analysis
        polyterm timing "trump"      # Check trading conditions
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

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing timing...", total=None)

            # Find market
            markets = gamma_client.search_markets(market_search, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Market not found'})
                else:
                    console.print(f"[yellow]Market '{market_search}' not found.[/yellow]")
                return

            market = markets[0]
            title = market.get('question', market.get('title', ''))

            # Get CLOB token
            clob_tokens = market.get('clobTokenIds', [])
            if isinstance(clob_tokens, str):
                import json
                try:
                    clob_tokens = json.loads(clob_tokens)
                except Exception:
                    clob_tokens = []
            token_id = clob_tokens[0] if clob_tokens and len(clob_tokens) > 0 else None

            # Get order book
            orderbook = None
            if token_id:
                try:
                    orderbook = clob_client.get_order_book(token_id)
                except Exception:
                    pass

            # Calculate timing factors
            timing_data = _analyze_timing(market, orderbook)

    finally:
        gamma_client.close()
        clob_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'market': title,
            'timing': timing_data,
        })
        return

    # Display
    console.print()
    console.print(Panel(f"[bold]Timing Analysis[/bold]\n{title[:60]}", border_style="cyan"))
    console.print()

    # Overall timing score
    score = timing_data['overall_score']
    if score >= 80:
        score_str = f"[green]EXCELLENT ({score}/100)[/green]"
        verdict = "Great time to trade"
    elif score >= 60:
        score_str = f"[green]GOOD ({score}/100)[/green]"
        verdict = "Favorable conditions"
    elif score >= 40:
        score_str = f"[yellow]FAIR ({score}/100)[/yellow]"
        verdict = "Acceptable but not ideal"
    else:
        score_str = f"[red]POOR ({score}/100)[/red]"
        verdict = "Consider waiting"

    console.print(f"[bold]Trading Conditions:[/bold] {score_str}")
    console.print(f"[dim]{verdict}[/dim]")
    console.print()

    # Factor breakdown
    console.print("[bold]Factor Analysis:[/bold]")
    console.print()

    factors_table = Table(show_header=True, header_style="bold cyan", box=None)
    factors_table.add_column("Factor", width=18)
    factors_table.add_column("Status", width=12, justify="center")
    factors_table.add_column("Score", width=8, justify="center")
    factors_table.add_column("Impact", width=25)

    for factor in timing_data['factors']:
        if factor['score'] >= 70:
            status = f"[green]{factor['status']}[/green]"
        elif factor['score'] >= 40:
            status = f"[yellow]{factor['status']}[/yellow]"
        else:
            status = f"[red]{factor['status']}[/red]"

        score_bar = _score_bar(factor['score'])

        factors_table.add_row(
            factor['name'],
            status,
            score_bar,
            factor['impact'],
        )

    console.print(factors_table)
    console.print()

    # Timing windows
    console.print("[bold]Best Trading Windows:[/bold]")
    console.print()

    for window in timing_data['windows']:
        if window['quality'] == 'optimal':
            icon = "[green]●[/green]"
        elif window['quality'] == 'good':
            icon = "[yellow]●[/yellow]"
        else:
            icon = "[red]●[/red]"

        console.print(f"  {icon} {window['description']}")

    console.print()

    # Action recommendations
    console.print("[bold]Recommendations:[/bold]")
    console.print()

    for action in timing_data['actions']:
        if action['type'] == 'do':
            icon = "[green]✓[/green]"
        elif action['type'] == 'avoid':
            icon = "[red]✗[/red]"
        else:
            icon = "[yellow]~[/yellow]"

        console.print(f"  {icon} {action['text']}")

    console.print()

    # Market-specific timing
    if timing_data['event_timing']:
        console.print("[bold]Event Timing:[/bold]")
        console.print(f"  [cyan]•[/cyan] {timing_data['event_timing']}")
        console.print()


def _analyze_timing(market: dict, orderbook: dict) -> dict:
    """Analyze timing factors for trading"""
    factors = []

    price = _get_price(market)
    volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
    liquidity = market.get('liquidity', 0) or 0

    # 1. Spread Factor
    spread_score, spread_status, spread_impact = _analyze_spread(market, orderbook)
    factors.append({
        'name': 'Spread',
        'score': spread_score,
        'status': spread_status,
        'impact': spread_impact,
    })

    # 2. Volume Factor
    volume_score, volume_status, volume_impact = _analyze_volume(volume_24h, market.get('volume', 0))
    factors.append({
        'name': 'Volume',
        'score': volume_score,
        'status': volume_status,
        'impact': volume_impact,
    })

    # 3. Liquidity Factor
    liq_score, liq_status, liq_impact = _analyze_liquidity(liquidity, volume_24h)
    factors.append({
        'name': 'Liquidity',
        'score': liq_score,
        'status': liq_status,
        'impact': liq_impact,
    })

    # 4. Momentum Factor
    mom_score, mom_status, mom_impact = _analyze_momentum(market)
    factors.append({
        'name': 'Momentum',
        'score': mom_score,
        'status': mom_status,
        'impact': mom_impact,
    })

    # 5. Price Level Factor
    price_score, price_status, price_impact = _analyze_price_level(price)
    factors.append({
        'name': 'Price Level',
        'score': price_score,
        'status': price_status,
        'impact': price_impact,
    })

    # Calculate overall score (weighted average)
    weights = [0.25, 0.20, 0.20, 0.20, 0.15]  # Spread most important
    overall_score = sum(f['score'] * w for f, w in zip(factors, weights))

    # Trading windows
    windows = _get_trading_windows(factors, market)

    # Action recommendations
    actions = _get_actions(factors, overall_score)

    # Event timing
    event_timing = _get_event_timing(market)

    return {
        'overall_score': int(overall_score),
        'factors': factors,
        'windows': windows,
        'actions': actions,
        'event_timing': event_timing,
    }


def _analyze_spread(market: dict, orderbook: dict) -> tuple:
    """Analyze spread factor"""
    if orderbook:
        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])
        best_bid = float(bids[0].get('price', 0)) if bids else 0
        best_ask = float(asks[0].get('price', 1)) if asks else 1
    else:
        price = _get_price(market)
        best_bid = max(0.01, price - 0.02)
        best_ask = min(0.99, price + 0.02)

    spread = best_ask - best_bid
    spread_pct = spread / ((best_bid + best_ask) / 2) if (best_bid + best_ask) > 0 else 0

    if spread_pct < 0.02:
        return 90, "Tight", "Minimal cost to trade"
    elif spread_pct < 0.04:
        return 70, "Normal", "Typical trading cost"
    elif spread_pct < 0.08:
        return 45, "Wide", "Higher cost - use limits"
    else:
        return 20, "Very Wide", "Wait for better spread"


def _analyze_volume(volume_24h: float, total_volume: float) -> tuple:
    """Analyze volume factor"""
    if volume_24h > 100000:
        return 90, "High", "Strong trading interest"
    elif volume_24h > 25000:
        return 70, "Good", "Healthy activity"
    elif volume_24h > 5000:
        return 50, "Moderate", "Adequate for small trades"
    else:
        return 25, "Low", "May face slippage"


def _analyze_liquidity(liquidity: float, volume_24h: float) -> tuple:
    """Analyze liquidity factor"""
    if liquidity == 0:
        return 50, "Unknown", "Check order book"

    if liquidity > 100000:
        return 90, "Deep", "Large orders possible"
    elif liquidity > 25000:
        return 70, "Good", "Medium orders ok"
    elif liquidity > 5000:
        return 45, "Thin", "Keep orders small"
    else:
        return 20, "Very Thin", "Minimal size only"


def _analyze_momentum(market: dict) -> tuple:
    """Analyze momentum factor"""
    change = market.get('priceChange24h', 0)
    if not change:
        current = _get_price(market)
        prev = market.get('price24hAgo', 0)
        if prev and prev > 0:
            change = (current - prev) / prev

    if abs(change) < 0.02:
        return 80, "Stable", "Low volatility entry"
    elif abs(change) < 0.05:
        return 65, "Moving", "Normal volatility"
    elif abs(change) < 0.10:
        return 45, "Volatile", "Wait for stability"
    else:
        return 25, "Extreme", "High risk timing"


def _analyze_price_level(price: float) -> tuple:
    """Analyze price level factor"""
    if 0.30 <= price <= 0.70:
        return 80, "Mid-range", "Good upside potential"
    elif 0.15 <= price <= 0.85:
        return 60, "Moderate", "Some room to move"
    elif price < 0.15:
        return 70, "Low", "Cheap but risky"
    else:
        return 50, "High", "Limited upside"


def _get_trading_windows(factors: list, market: dict) -> list:
    """Get trading window recommendations"""
    windows = []

    spread_score = factors[0]['score']
    volume_score = factors[1]['score']

    if spread_score >= 70 and volume_score >= 60:
        windows.append({
            'quality': 'optimal',
            'description': 'Now - Spread tight and volume healthy',
        })
    elif spread_score >= 50:
        windows.append({
            'quality': 'good',
            'description': 'Place limit order at mid-price',
        })
    else:
        windows.append({
            'quality': 'poor',
            'description': 'Wait for spread to tighten',
        })

    # Time-based recommendations
    now = datetime.now()
    if 9 <= now.hour <= 17:
        windows.append({
            'quality': 'good',
            'description': 'US market hours - typically higher volume',
        })
    else:
        windows.append({
            'quality': 'fair',
            'description': 'Off-peak hours - may have wider spreads',
        })

    return windows


def _get_actions(factors: list, overall_score: float) -> list:
    """Get action recommendations"""
    actions = []

    if overall_score >= 70:
        actions.append({'type': 'do', 'text': 'Market order acceptable for small trades'})
        actions.append({'type': 'do', 'text': 'Good entry point for position building'})
    elif overall_score >= 50:
        actions.append({'type': 'consider', 'text': 'Use limit orders to improve fill price'})
        actions.append({'type': 'consider', 'text': 'Start with smaller position size'})
    else:
        actions.append({'type': 'avoid', 'text': 'Avoid market orders - use limits only'})
        actions.append({'type': 'avoid', 'text': 'Wait for better conditions if possible'})

    # Factor-specific advice
    if factors[0]['score'] < 50:  # Spread
        actions.append({'type': 'avoid', 'text': f"Spread is wide - limit orders essential"})

    if factors[3]['score'] < 50:  # Momentum
        actions.append({'type': 'consider', 'text': 'High volatility - consider waiting'})

    return actions[:4]  # Limit to 4 actions


def _get_event_timing(market: dict) -> str:
    """Get event-specific timing advice"""
    end_date_str = market.get('endDate', market.get('end_date', ''))
    if not end_date_str:
        return None

    try:
        if 'T' in end_date_str:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
        else:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

        if end_date.tzinfo:
            end_date = end_date.replace(tzinfo=None)

        days_until = (end_date - datetime.now()).days

        if days_until <= 1:
            return "Resolution imminent - high risk/reward timing"
        elif days_until <= 7:
            return f"Resolves in {days_until} days - momentum may accelerate"
        elif days_until <= 30:
            return f"Resolves in {days_until} days - time to build position"
        else:
            return f"Long-dated ({days_until} days) - price may drift"

    except Exception:
        return None


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            import json
            prices = market['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))


def _score_bar(score: int) -> str:
    """Create visual score bar"""
    filled = score // 10
    empty = 10 - filled

    if score >= 70:
        color = "green"
    elif score >= 40:
        color = "yellow"
    else:
        color = "red"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
