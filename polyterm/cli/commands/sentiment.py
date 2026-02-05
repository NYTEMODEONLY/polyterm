"""Market Sentiment - Analyze market sentiment from multiple signals"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", "search_term", default=None, help="Market to analyze")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def sentiment(ctx, search_term, interactive, output_format):
    """Analyze market sentiment from multiple signals

    Combines volume, price momentum, whale activity, and order book
    data to provide an overall sentiment score.

    Examples:
        polyterm sentiment -m "bitcoin"       # Sentiment for market
        polyterm sentiment --interactive      # Interactive selection
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        search_term = Prompt.ask("[cyan]Search for market[/cyan]", default="")

    if not search_term:
        console.print("[yellow]Please specify a market with -m or use --interactive[/yellow]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )

    db = Database()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing sentiment...", total=None)

            # Find market
            markets = gamma_client.search_markets(search_term, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
                else:
                    console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
                return

            market = markets[0]
            market_id = market.get('id', market.get('condition_id', ''))

            # Get CLOB token
            clob_tokens = market.get('clobTokenIds', [])
            if isinstance(clob_tokens, str):
                import json
                try:
                    clob_tokens = json.loads(clob_tokens)
                except Exception:
                    clob_tokens = []
            clob_token = clob_tokens[0] if clob_tokens and len(clob_tokens) > 0 else ''

            title = market.get('question', market.get('title', ''))[:60]

            # Collect sentiment signals
            signals = []

            # 1. Price momentum signal
            current_price = _get_current_price(market)
            price_signal = _analyze_price_momentum(market)
            signals.append(price_signal)

            # 2. Volume signal
            volume_signal = _analyze_volume(market)
            signals.append(volume_signal)

            # 3. Orderbook signal (if available)
            orderbook_signal = _analyze_orderbook(clob_client, clob_token)
            if orderbook_signal:
                signals.append(orderbook_signal)

            # 4. Recent trades signal
            trades_signal = _analyze_recent_trades(clob_client, clob_token)
            if trades_signal:
                signals.append(trades_signal)

            # 5. Whale signal (from tracked wallets)
            whale_signal = _analyze_whale_activity(db, market_id)
            if whale_signal:
                signals.append(whale_signal)

            # Calculate overall sentiment
            overall = _calculate_overall_sentiment(signals)

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'current_price': current_price,
                'sentiment': overall,
                'signals': [s.__dict__ if hasattr(s, '__dict__') else s for s in signals],
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
        console.print()

        # Overall sentiment display
        sentiment_color = _get_sentiment_color(overall['score'])
        console.print(f"[bold]Overall Sentiment:[/bold] [{sentiment_color}]{overall['label']}[/{sentiment_color}]")
        console.print()

        # Sentiment meter
        _display_sentiment_meter(console, overall['score'])
        console.print()

        # Signal breakdown
        console.print("[bold]Signal Breakdown:[/bold]")
        console.print()

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Signal", width=15)
        table.add_column("Score", width=10, justify="center")
        table.add_column("Weight", width=8, justify="center")
        table.add_column("Analysis")

        for signal in signals:
            score_color = _get_sentiment_color(signal['score'])
            table.add_row(
                signal['name'],
                f"[{score_color}]{signal['score']:+.1f}[/{score_color}]",
                f"{signal['weight']:.1f}x",
                signal['reason'],
            )

        console.print(table)
        console.print()

        # Current price context
        console.print(f"[dim]Current Price: {current_price:.1%}[/dim]")
        console.print()

        # Interpretation
        console.print("[bold]Interpretation:[/bold]")
        _display_interpretation(console, overall, current_price)
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()


def _get_current_price(market: dict) -> float:
    """Get current market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)


def _analyze_price_momentum(market: dict) -> dict:
    """Analyze price momentum from 24h change"""
    score = 0
    reason = "No momentum data"

    # Try to get price changes
    price_change_24h = float(market.get('priceChange24h', 0) or 0)
    if not price_change_24h:
        # Calculate from other fields if available
        current = _get_current_price(market)
        prev = market.get('price24hAgo', current)
        try:
            prev = float(prev) if prev else 0
        except (ValueError, TypeError):
            prev = 0
        if prev > 0:
            price_change_24h = (current - prev) / prev

    if price_change_24h:
        # Convert to sentiment score (-1 to +1)
        # Strong moves > 5% get full score
        score = max(-1, min(1, price_change_24h * 10))

        if abs(price_change_24h) < 0.01:
            reason = "Price stable (low momentum)"
        elif price_change_24h > 0.05:
            reason = f"Strong bullish momentum (+{price_change_24h:.1%})"
        elif price_change_24h > 0:
            reason = f"Mild bullish momentum (+{price_change_24h:.1%})"
        elif price_change_24h < -0.05:
            reason = f"Strong bearish momentum ({price_change_24h:.1%})"
        else:
            reason = f"Mild bearish momentum ({price_change_24h:.1%})"

    return {
        'name': 'Momentum',
        'score': score,
        'weight': 1.5,
        'reason': reason,
    }


def _analyze_volume(market: dict) -> dict:
    """Analyze volume trends"""
    score = 0
    reason = "No volume data"

    volume_24h = market.get('volume24hr', market.get('volume24h', 0))
    volume_total = market.get('volume', 0)

    if volume_24h and volume_total and volume_total > 0:
        # High recent volume relative to total is bullish (activity)
        volume_ratio = volume_24h / volume_total

        if volume_ratio > 0.1:  # >10% of total in last 24h
            score = 0.5
            reason = f"High activity (24h vol = {volume_ratio:.1%} of total)"
        elif volume_ratio > 0.05:
            score = 0.25
            reason = f"Moderate activity (24h vol = {volume_ratio:.1%} of total)"
        else:
            score = -0.1
            reason = f"Low activity (24h vol = {volume_ratio:.1%} of total)"
    elif volume_24h:
        if volume_24h > 100000:
            score = 0.4
            reason = f"High 24h volume (${volume_24h:,.0f})"
        elif volume_24h > 10000:
            score = 0.2
            reason = f"Moderate 24h volume (${volume_24h:,.0f})"
        else:
            score = 0
            reason = f"Low 24h volume (${volume_24h:,.0f})"

    return {
        'name': 'Volume',
        'score': score,
        'weight': 1.0,
        'reason': reason,
    }


def _analyze_orderbook(clob_client: CLOBClient, token_id: str) -> dict:
    """Analyze order book depth and imbalance"""
    if not token_id:
        return None

    try:
        orderbook = clob_client.get_order_book(token_id)
        if not orderbook:
            return None

        bids = orderbook.get('bids', [])
        asks = orderbook.get('asks', [])

        if not bids and not asks:
            return None

        # Calculate bid/ask depth
        bid_depth = sum(float(b.get('size', 0)) for b in bids[:10])
        ask_depth = sum(float(a.get('size', 0)) for a in asks[:10])

        total_depth = bid_depth + ask_depth
        if total_depth == 0:
            return None

        # Imbalance: more bids = bullish, more asks = bearish
        imbalance = (bid_depth - ask_depth) / total_depth
        score = imbalance  # -1 to +1

        if imbalance > 0.3:
            reason = f"Strong bid support ({bid_depth:.0f} vs {ask_depth:.0f})"
        elif imbalance > 0:
            reason = f"Slight bid support ({bid_depth:.0f} vs {ask_depth:.0f})"
        elif imbalance < -0.3:
            reason = f"Heavy selling pressure ({ask_depth:.0f} asks vs {bid_depth:.0f} bids)"
        else:
            reason = f"Balanced orderbook ({bid_depth:.0f} bids, {ask_depth:.0f} asks)"

        return {
            'name': 'Order Book',
            'score': score,
            'weight': 1.2,
            'reason': reason,
        }
    except Exception:
        return None


def _analyze_recent_trades(clob_client: CLOBClient, token_id: str) -> dict:
    """Analyze recent trade flow"""
    if not token_id:
        return None

    try:
        trades = clob_client.get_trades(token_id, limit=50)
        if not trades or len(trades) < 5:
            return None

        # Analyze buy vs sell pressure from recent trades
        buy_volume = 0
        sell_volume = 0

        for trade in trades:
            size = float(trade.get('size', 0))
            side = trade.get('side', '').lower()

            if side == 'buy':
                buy_volume += size
            elif side == 'sell':
                sell_volume += size

        total = buy_volume + sell_volume
        if total == 0:
            return None

        imbalance = (buy_volume - sell_volume) / total
        score = imbalance

        if imbalance > 0.3:
            reason = f"Strong buy pressure ({buy_volume:.0f} bought vs {sell_volume:.0f} sold)"
        elif imbalance > 0:
            reason = f"Slight buy bias in recent trades"
        elif imbalance < -0.3:
            reason = f"Strong sell pressure ({sell_volume:.0f} sold vs {buy_volume:.0f} bought)"
        else:
            reason = "Balanced trade flow"

        return {
            'name': 'Trade Flow',
            'score': score,
            'weight': 1.3,
            'reason': reason,
        }
    except Exception:
        return None


def _analyze_whale_activity(db: Database, market_id: str) -> dict:
    """Analyze whale activity from tracked wallets"""
    try:
        # Get recent whale alerts for this market
        alerts = db.get_unacknowledged_alerts()
        whale_alerts = [a for a in alerts if a.market_id == market_id and 'whale' in (a.alert_type or '').lower()]

        if not whale_alerts:
            return None

        # Analyze whale positions
        bullish = 0
        bearish = 0

        for alert in whale_alerts[-10:]:  # Last 10 whale alerts
            data = alert.data if hasattr(alert, 'data') else {}
            if data is None:
                data = {}
            if isinstance(data, str):
                import json
                try:
                    data = json.loads(data)
                except (json.JSONDecodeError, ValueError):
                    data = {}

            side = data.get('side', '').lower() if isinstance(data, dict) else ''
            size = data.get('size', 0) if isinstance(data, dict) else 0

            if side == 'buy' or side == 'yes':
                bullish += size
            elif side == 'sell' or side == 'no':
                bearish += size

        total = bullish + bearish
        if total == 0:
            return None

        imbalance = (bullish - bearish) / total
        score = imbalance * 0.8  # Cap at 0.8

        if imbalance > 0.5:
            reason = "Whales accumulating YES"
        elif imbalance > 0:
            reason = "Slight whale bullish bias"
        elif imbalance < -0.5:
            reason = "Whales accumulating NO"
        else:
            reason = "Mixed whale positioning"

        return {
            'name': 'Whale Activity',
            'score': score,
            'weight': 1.5,
            'reason': reason,
        }
    except Exception:
        return None


def _calculate_overall_sentiment(signals: list) -> dict:
    """Calculate weighted average sentiment"""
    if not signals:
        return {'score': 0, 'label': 'Neutral'}

    total_weight = sum(s['weight'] for s in signals)
    weighted_sum = sum(s['score'] * s['weight'] for s in signals)

    if total_weight == 0:
        score = 0
    else:
        score = weighted_sum / total_weight

    # Determine label
    if score >= 0.5:
        label = "Very Bullish"
    elif score >= 0.2:
        label = "Bullish"
    elif score >= 0.05:
        label = "Slightly Bullish"
    elif score <= -0.5:
        label = "Very Bearish"
    elif score <= -0.2:
        label = "Bearish"
    elif score <= -0.05:
        label = "Slightly Bearish"
    else:
        label = "Neutral"

    return {
        'score': score,
        'label': label,
        'signal_count': len(signals),
    }


def _get_sentiment_color(score: float) -> str:
    """Get color for sentiment score"""
    if score >= 0.3:
        return "green"
    elif score >= 0.1:
        return "bright_green"
    elif score <= -0.3:
        return "red"
    elif score <= -0.1:
        return "bright_red"
    return "yellow"


def _display_sentiment_meter(console: Console, score: float):
    """Display ASCII sentiment meter"""
    # Score from -1 to +1, meter is 20 chars
    normalized = int((score + 1) * 10)  # 0 to 20
    normalized = max(0, min(20, normalized))

    meter = ""
    for i in range(21):
        if i == normalized:
            meter += "[bold bright_white]O[/bold bright_white]"
        elif i == 10:
            meter += "|"  # Center
        elif i < 10:
            meter += "[red]-[/red]"
        else:
            meter += "[green]+[/green]"

    console.print(f"Bearish {meter} Bullish")


def _display_interpretation(console: Console, overall: dict, current_price: float):
    """Display sentiment interpretation"""
    score = overall['score']
    label = overall['label']

    # Price context
    if current_price > 0.7:
        price_context = "already trading high"
    elif current_price < 0.3:
        price_context = "trading at low levels"
    else:
        price_context = "at mid-range prices"

    if score >= 0.3:
        console.print(f"[green]Strong bullish signals detected. Market sentiment favors YES.[/green]")
        if current_price > 0.7:
            console.print("[yellow]Note: Price already high - limited upside potential.[/yellow]")
    elif score >= 0.1:
        console.print(f"[bright_green]Mildly bullish sentiment. More buyers than sellers recently.[/bright_green]")
    elif score <= -0.3:
        console.print(f"[red]Strong bearish signals detected. Market sentiment favors NO.[/red]")
        if current_price < 0.3:
            console.print("[yellow]Note: Price already low - limited downside potential.[/yellow]")
    elif score <= -0.1:
        console.print(f"[bright_red]Mildly bearish sentiment. Selling pressure observed.[/bright_red]")
    else:
        console.print(f"[yellow]Mixed signals. No clear directional bias detected.[/yellow]")

    console.print()
    console.print(f"[dim]Market is {price_context}. Sentiment based on {overall['signal_count']} signals.[/dim]")
