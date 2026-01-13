"""Market Signals - Entry/exit timing signals based on multiple factors"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", default=None, help="Analyze specific market")
@click.option("--scan", "-s", is_flag=True, help="Scan all markets for signals")
@click.option("--type", "-t", "signal_type", type=click.Choice(["all", "entry", "exit"]), default="all", help="Signal type")
@click.option("--min-strength", type=int, default=60, help="Minimum signal strength (0-100)")
@click.option("--limit", "-l", default=20, help="Number of markets to scan")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def signals(ctx, market, scan, signal_type, min_strength, limit, output_format):
    """Detect entry and exit signals for markets

    Analyzes multiple factors to generate trading signals:
    - Volume spikes (unusual activity)
    - Price momentum (breakouts/breakdowns)
    - Whale activity (accumulation/distribution)
    - Technical indicators (overbought/oversold)

    Examples:
        polyterm signals --market "bitcoin"     # Analyze specific market
        polyterm signals --scan                 # Scan for opportunities
        polyterm signals --type entry           # Entry signals only
        polyterm signals --min-strength 70      # Strong signals only
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        if market:
            _analyze_market_signals(console, gamma_client, market, output_format)
        else:
            _scan_for_signals(console, gamma_client, signal_type, min_strength, limit, output_format)

    finally:
        gamma_client.close()


def _analyze_market_signals(console: Console, gamma_client: GammaClient, search_term: str, output_format: str):
    """Analyze signals for a specific market"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Analyzing market...", total=None)

        markets = gamma_client.search_markets(search_term, limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Market not found'})
            else:
                console.print(f"[yellow]Market '{search_term}' not found.[/yellow]")
            return

        market = markets[0]
        signals_data = _calculate_signals(market)

    if output_format == 'json':
        print_json({
            'success': True,
            'market': market.get('question', market.get('title', '')),
            'signals': signals_data,
        })
        return

    title = market.get('question', market.get('title', ''))[:60]
    price = _get_price(market)

    console.print()
    console.print(Panel(f"[bold]Signal Analysis[/bold]\n{title}", border_style="cyan"))
    console.print()

    console.print(f"[bold]Current Price:[/bold] {price:.1%}")
    console.print()

    # Overall signal
    overall = signals_data['overall']
    if overall['direction'] == 'bullish':
        dir_str = f"[green]BULLISH[/green]"
    elif overall['direction'] == 'bearish':
        dir_str = f"[red]BEARISH[/red]"
    else:
        dir_str = f"[yellow]NEUTRAL[/yellow]"

    console.print(f"[bold]Overall Signal:[/bold] {dir_str} (Strength: {overall['strength']}/100)")
    console.print()

    # Individual signals
    console.print("[bold]Signal Breakdown:[/bold]")
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Signal", width=20)
    table.add_column("Reading", width=15, justify="center")
    table.add_column("Strength", width=10, justify="center")
    table.add_column("Note", max_width=30)

    for signal in signals_data['signals']:
        reading = signal['reading']
        if signal['bullish']:
            reading_str = f"[green]{reading}[/green]"
        elif signal['bearish']:
            reading_str = f"[red]{reading}[/red]"
        else:
            reading_str = f"[yellow]{reading}[/yellow]"

        strength_bar = _strength_bar(signal['strength'])

        table.add_row(
            signal['name'],
            reading_str,
            strength_bar,
            signal.get('note', ''),
        )

    console.print(table)
    console.print()

    # Action suggestion
    console.print("[bold]Suggested Action:[/bold]")
    if overall['strength'] >= 70:
        if overall['direction'] == 'bullish':
            console.print("[green]Strong entry signal - consider buying YES[/green]")
        elif overall['direction'] == 'bearish':
            console.print("[red]Strong exit/short signal - consider selling or buying NO[/red]")
    elif overall['strength'] >= 50:
        if overall['direction'] == 'bullish':
            console.print("[yellow]Moderate bullish - wait for confirmation or enter small[/yellow]")
        elif overall['direction'] == 'bearish':
            console.print("[yellow]Moderate bearish - tighten stops or reduce position[/yellow]")
    else:
        console.print("[dim]No clear signal - wait for better setup[/dim]")

    console.print()


def _scan_for_signals(console: Console, gamma_client: GammaClient, signal_type: str, min_strength: int, limit: int, output_format: str):
    """Scan markets for trading signals"""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Scanning markets...", total=None)

        # Get active markets
        markets = gamma_client.get_markets(limit=limit * 2, active=True)

        results = []
        for market in markets[:limit * 2]:
            signals_data = _calculate_signals(market)
            overall = signals_data['overall']

            # Filter by type
            if signal_type == 'entry' and overall['direction'] != 'bullish':
                continue
            if signal_type == 'exit' and overall['direction'] != 'bearish':
                continue

            # Filter by strength
            if overall['strength'] >= min_strength:
                results.append({
                    'market': market,
                    'signals': signals_data,
                })

        results.sort(key=lambda x: x['signals']['overall']['strength'], reverse=True)
        results = results[:limit]

    if output_format == 'json':
        print_json({
            'success': True,
            'count': len(results),
            'signal_type': signal_type,
            'min_strength': min_strength,
            'results': [{
                'title': r['market'].get('question', r['market'].get('title', '')),
                'signals': r['signals'],
            } for r in results],
        })
        return

    console.print()
    type_label = signal_type.upper() if signal_type != 'all' else 'ALL'
    console.print(Panel(f"[bold]Market Signals Scan[/bold]\nType: {type_label} | Min Strength: {min_strength}", border_style="cyan"))
    console.print()

    if not results:
        console.print(f"[yellow]No signals found matching criteria.[/yellow]")
        console.print("[dim]Try lowering --min-strength or scanning more markets with --limit[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Market", max_width=40)
    table.add_column("Price", width=8, justify="center")
    table.add_column("Signal", width=10, justify="center")
    table.add_column("Strength", width=10, justify="center")
    table.add_column("Key Factor", width=18)

    for r in results:
        market = r['market']
        sigs = r['signals']
        overall = sigs['overall']

        title = market.get('question', market.get('title', ''))[:38]
        price = _get_price(market)

        if overall['direction'] == 'bullish':
            sig_str = "[green]BUY[/green]"
        elif overall['direction'] == 'bearish':
            sig_str = "[red]SELL[/red]"
        else:
            sig_str = "[yellow]HOLD[/yellow]"

        strength_bar = _strength_bar(overall['strength'])

        # Find strongest individual signal
        strongest = max(sigs['signals'], key=lambda s: s['strength'])
        key_factor = f"{strongest['name']}: {strongest['reading']}"

        table.add_row(title, f"{price:.0%}", sig_str, strength_bar, key_factor)

    console.print(table)
    console.print()
    console.print(f"[dim]{len(results)} signals found[/dim]")
    console.print("[dim]Analyze individual markets with: polyterm signals -m <market>[/dim]")
    console.print()


def _calculate_signals(market: dict) -> dict:
    """Calculate trading signals for a market"""
    signals = []

    price = _get_price(market)
    volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
    total_volume = market.get('volume', 0) or 0
    liquidity = market.get('liquidity', 0) or 0

    # 1. Volume Signal
    volume_signal = _volume_signal(volume_24h, total_volume)
    signals.append(volume_signal)

    # 2. Price Momentum Signal
    momentum_signal = _momentum_signal(market)
    signals.append(momentum_signal)

    # 3. Liquidity Signal
    liquidity_signal = _liquidity_signal(liquidity, volume_24h)
    signals.append(liquidity_signal)

    # 4. Technical Signal (price position)
    tech_signal = _technical_signal(price)
    signals.append(tech_signal)

    # 5. Activity Signal (trading frequency)
    activity_signal = _activity_signal(volume_24h, total_volume)
    signals.append(activity_signal)

    # Calculate overall signal
    bullish_strength = sum(s['strength'] for s in signals if s['bullish'])
    bearish_strength = sum(s['strength'] for s in signals if s['bearish'])
    neutral_strength = sum(s['strength'] for s in signals if not s['bullish'] and not s['bearish'])

    total_strength = bullish_strength + bearish_strength + neutral_strength
    if total_strength == 0:
        total_strength = 1

    if bullish_strength > bearish_strength + 20:
        direction = 'bullish'
        strength = min(100, int((bullish_strength / total_strength) * 100))
    elif bearish_strength > bullish_strength + 20:
        direction = 'bearish'
        strength = min(100, int((bearish_strength / total_strength) * 100))
    else:
        direction = 'neutral'
        strength = max(30, 50 - abs(bullish_strength - bearish_strength))

    return {
        'signals': signals,
        'overall': {
            'direction': direction,
            'strength': strength,
            'bullish_score': bullish_strength,
            'bearish_score': bearish_strength,
        }
    }


def _volume_signal(volume_24h: float, total_volume: float) -> dict:
    """Analyze volume for unusual activity"""
    if total_volume == 0:
        return {
            'name': 'Volume Spike',
            'reading': 'No data',
            'strength': 0,
            'bullish': False,
            'bearish': False,
            'note': 'Insufficient volume history',
        }

    # Calculate what % of total volume happened in last 24h
    volume_ratio = volume_24h / total_volume if total_volume > 0 else 0

    if volume_ratio > 0.15:  # >15% of all-time volume in 24h
        return {
            'name': 'Volume Spike',
            'reading': 'Very High',
            'strength': 30,
            'bullish': True,
            'bearish': False,
            'note': f'{volume_ratio:.1%} of total vol in 24h',
        }
    elif volume_ratio > 0.08:
        return {
            'name': 'Volume Spike',
            'reading': 'High',
            'strength': 20,
            'bullish': True,
            'bearish': False,
            'note': 'Above average activity',
        }
    elif volume_ratio > 0.03:
        return {
            'name': 'Volume Spike',
            'reading': 'Normal',
            'strength': 10,
            'bullish': False,
            'bearish': False,
            'note': 'Typical trading activity',
        }
    else:
        return {
            'name': 'Volume Spike',
            'reading': 'Low',
            'strength': 15,
            'bullish': False,
            'bearish': True,
            'note': 'Below average - less interest',
        }


def _momentum_signal(market: dict) -> dict:
    """Analyze price momentum"""
    price_change = market.get('priceChange24h', 0)

    if not price_change:
        current = _get_price(market)
        prev = market.get('price24hAgo', 0)
        if prev and prev > 0:
            price_change = (current - prev) / prev

    if price_change > 0.10:  # >10% up
        return {
            'name': 'Momentum',
            'reading': 'Strong Up',
            'strength': 25,
            'bullish': True,
            'bearish': False,
            'note': f'+{price_change:.1%} in 24h',
        }
    elif price_change > 0.03:
        return {
            'name': 'Momentum',
            'reading': 'Up',
            'strength': 15,
            'bullish': True,
            'bearish': False,
            'note': f'+{price_change:.1%} in 24h',
        }
    elif price_change < -0.10:
        return {
            'name': 'Momentum',
            'reading': 'Strong Down',
            'strength': 25,
            'bullish': False,
            'bearish': True,
            'note': f'{price_change:.1%} in 24h',
        }
    elif price_change < -0.03:
        return {
            'name': 'Momentum',
            'reading': 'Down',
            'strength': 15,
            'bullish': False,
            'bearish': True,
            'note': f'{price_change:.1%} in 24h',
        }
    else:
        return {
            'name': 'Momentum',
            'reading': 'Flat',
            'strength': 10,
            'bullish': False,
            'bearish': False,
            'note': 'Consolidating',
        }


def _liquidity_signal(liquidity: float, volume_24h: float) -> dict:
    """Analyze liquidity relative to volume"""
    if liquidity == 0:
        return {
            'name': 'Liquidity',
            'reading': 'Unknown',
            'strength': 0,
            'bullish': False,
            'bearish': False,
            'note': 'No liquidity data',
        }

    # High liquidity relative to volume = easier to trade
    liq_vol_ratio = liquidity / volume_24h if volume_24h > 0 else liquidity / 1000

    if liq_vol_ratio > 5:
        return {
            'name': 'Liquidity',
            'reading': 'Deep',
            'strength': 15,
            'bullish': True,
            'bearish': False,
            'note': 'Easy entry/exit',
        }
    elif liq_vol_ratio > 1:
        return {
            'name': 'Liquidity',
            'reading': 'Good',
            'strength': 10,
            'bullish': False,
            'bearish': False,
            'note': 'Adequate depth',
        }
    else:
        return {
            'name': 'Liquidity',
            'reading': 'Thin',
            'strength': 20,
            'bullish': False,
            'bearish': True,
            'note': 'Slippage risk',
        }


def _technical_signal(price: float) -> dict:
    """Technical signal based on price extremes"""
    if price > 0.85:
        return {
            'name': 'Price Level',
            'reading': 'Overbought',
            'strength': 20,
            'bullish': False,
            'bearish': True,
            'note': 'Near ceiling - limited upside',
        }
    elif price < 0.15:
        return {
            'name': 'Price Level',
            'reading': 'Oversold',
            'strength': 20,
            'bullish': True,
            'bearish': False,
            'note': 'Near floor - potential bounce',
        }
    elif 0.40 <= price <= 0.60:
        return {
            'name': 'Price Level',
            'reading': 'Neutral Zone',
            'strength': 10,
            'bullish': False,
            'bearish': False,
            'note': 'Maximum uncertainty',
        }
    else:
        return {
            'name': 'Price Level',
            'reading': 'Mid-range',
            'strength': 5,
            'bullish': False,
            'bearish': False,
            'note': 'Room to move either way',
        }


def _activity_signal(volume_24h: float, total_volume: float) -> dict:
    """Signal based on trading activity level"""
    if volume_24h > 100000:
        return {
            'name': 'Activity',
            'reading': 'Very Active',
            'strength': 15,
            'bullish': True,
            'bearish': False,
            'note': f'${volume_24h:,.0f} 24h vol',
        }
    elif volume_24h > 25000:
        return {
            'name': 'Activity',
            'reading': 'Active',
            'strength': 10,
            'bullish': True,
            'bearish': False,
            'note': 'Good trading interest',
        }
    elif volume_24h > 5000:
        return {
            'name': 'Activity',
            'reading': 'Moderate',
            'strength': 5,
            'bullish': False,
            'bearish': False,
            'note': 'Average activity',
        }
    else:
        return {
            'name': 'Activity',
            'reading': 'Low',
            'strength': 15,
            'bullish': False,
            'bearish': True,
            'note': 'Limited interest',
        }


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


def _strength_bar(strength: int) -> str:
    """Create visual strength bar"""
    filled = strength // 10
    empty = 10 - filled

    if strength >= 70:
        color = "green"
    elif strength >= 40:
        color = "yellow"
    else:
        color = "red"

    return f"[{color}]{'█' * filled}{'░' * empty}[/{color}]"
