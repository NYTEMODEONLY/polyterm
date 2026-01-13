"""Market Statistics - Detailed market analysis and metrics"""

import click
import math
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...db.database import Database
from ...core.charts import ASCIIChart
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", default=None, help="Market ID or search term")
@click.option("--hours", "-h", "time_hours", default=24, help="Hours of history for analysis (default: 24)")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def stats(ctx, market, time_hours, output_format):
    """View detailed market statistics

    Shows volatility, price trends, volume analysis, and technical indicators.

    Examples:
        polyterm stats --market "bitcoin"
        polyterm stats -m "election" --hours 48
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    if not market:
        console.print(Panel(
            "[bold]Market Statistics[/bold]\n\n"
            "[dim]Get detailed analysis and metrics for any market.[/dim]",
            title="[cyan]Stats[/cyan]",
            border_style="cyan",
        ))
        console.print()
        market = Prompt.ask("[cyan]Enter market ID or search term[/cyan]")

    if not market:
        console.print("[yellow]No market specified.[/yellow]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Search for market
        console.print(f"[dim]Searching for: {market}[/dim]")
        markets = gamma_client.search_markets(market, limit=5)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': f'No markets found for "{market}"'})
            else:
                console.print(f"[yellow]No markets found matching '{market}'[/yellow]")
            return

        # Select market
        if len(markets) > 1 and output_format != 'json':
            console.print()
            console.print("[bold]Multiple markets found:[/bold]")
            for i, m in enumerate(markets, 1):
                title = m.get('question', m.get('title', 'Unknown'))[:50]
                console.print(f"  [cyan]{i}.[/cyan] {title}")

            console.print()
            choice = Prompt.ask(
                "[cyan]Select market[/cyan]",
                choices=[str(i) for i in range(1, len(markets) + 1)],
                default="1"
            )
            selected = markets[int(choice) - 1]
        else:
            selected = markets[0]

        market_id = selected.get('id', selected.get('condition_id', ''))
        title = selected.get('question', selected.get('title', ''))

        # Track view
        import json
        outcome_prices = selected.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []
        current_price = float(outcome_prices[0]) if outcome_prices else 0.5
        db.track_market_view(market_id, title[:100], current_price)

        # Get historical data
        snapshots = db.get_market_history(market_id, hours=time_hours)

        # Calculate statistics
        stats_data = _calculate_stats(selected, snapshots, time_hours)

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'hours': time_hours,
                **stats_data,
            })
        else:
            _display_stats(console, title, stats_data, snapshots, time_hours)

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _calculate_stats(market: dict, snapshots: list, hours: int) -> dict:
    """Calculate market statistics"""
    import json

    # Current metrics from market data
    outcome_prices = market.get('outcomePrices', [])
    if isinstance(outcome_prices, str):
        try:
            outcome_prices = json.loads(outcome_prices)
        except Exception:
            outcome_prices = []

    current_price = float(outcome_prices[0]) if outcome_prices else 0.5
    volume = float(market.get('volume', 0) or 0)
    liquidity = float(market.get('liquidity', 0) or 0)

    # End date analysis
    end_date_str = market.get('endDate', '')
    days_remaining = None
    if end_date_str:
        try:
            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
            end_date = end_date.replace(tzinfo=None)
            days_remaining = (end_date - datetime.now()).days
        except Exception:
            pass

    # Historical analysis
    if snapshots and len(snapshots) >= 2:
        prices = [s.probability for s in reversed(snapshots)]

        # Price changes
        first_price = prices[0]
        last_price = prices[-1]
        price_change = last_price - first_price
        price_change_pct = (price_change / first_price * 100) if first_price > 0 else 0

        # High/Low
        high_price = max(prices)
        low_price = min(prices)
        price_range = high_price - low_price

        # Volatility (standard deviation of returns)
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)

        if returns:
            mean_return = sum(returns) / len(returns)
            variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
            volatility = math.sqrt(variance) * 100  # As percentage
        else:
            volatility = 0

        # Trend analysis (simple linear regression slope)
        n = len(prices)
        x_mean = (n - 1) / 2
        y_mean = sum(prices) / n

        numerator = sum((i - x_mean) * (prices[i] - y_mean) for i in range(n))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        if denominator != 0:
            slope = numerator / denominator
            # Normalize slope to daily percentage change
            trend_daily = slope * (24 / hours) * len(prices) * 100
        else:
            trend_daily = 0

        # RSI (Relative Strength Index)
        gains = []
        losses = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        if gains and losses:
            avg_gain = sum(gains[-14:]) / min(14, len(gains))
            avg_loss = sum(losses[-14:]) / min(14, len(losses))

            if avg_loss > 0:
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
            else:
                rsi = 100
        else:
            rsi = 50

        # Momentum (price change velocity)
        if len(prices) >= 6:
            recent_change = prices[-1] - prices[-6]
            older_change = prices[-6] - prices[-min(12, len(prices))]
            momentum = "accelerating" if recent_change > older_change else "decelerating" if recent_change < older_change else "stable"
        else:
            momentum = "unknown"

    else:
        # No historical data
        price_change = 0
        price_change_pct = 0
        high_price = current_price
        low_price = current_price
        price_range = 0
        volatility = 0
        trend_daily = 0
        rsi = 50
        momentum = "unknown"

    # Market health indicators
    volume_per_liquidity = volume / liquidity if liquidity > 0 else 0

    # Implied probability confidence
    # Markets near 50% are uncertain, near 0%/100% are more certain
    certainty = abs(current_price - 0.5) * 2 * 100  # 0-100 scale

    return {
        'current': {
            'price': current_price,
            'volume': volume,
            'liquidity': liquidity,
            'days_remaining': days_remaining,
        },
        'price_analysis': {
            'change': price_change,
            'change_pct': price_change_pct,
            'high': high_price,
            'low': low_price,
            'range': price_range,
        },
        'volatility': {
            'std_dev': volatility,
            'level': 'High' if volatility > 5 else 'Medium' if volatility > 2 else 'Low',
        },
        'trend': {
            'direction': 'Up' if trend_daily > 0.5 else 'Down' if trend_daily < -0.5 else 'Sideways',
            'strength': abs(trend_daily),
            'daily_change_est': trend_daily,
        },
        'technical': {
            'rsi': rsi,
            'rsi_signal': 'Overbought' if rsi > 70 else 'Oversold' if rsi < 30 else 'Neutral',
            'momentum': momentum,
        },
        'health': {
            'volume_liquidity_ratio': volume_per_liquidity,
            'certainty': certainty,
            'data_points': len(snapshots) if snapshots else 0,
        },
    }


def _display_stats(console: Console, title: str, stats_data: dict, snapshots: list, hours: int):
    """Display statistics"""
    console.print()

    console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
    console.print()

    current = stats_data['current']
    price_analysis = stats_data['price_analysis']
    volatility = stats_data['volatility']
    trend = stats_data['trend']
    technical = stats_data['technical']
    health = stats_data['health']

    # Current state
    console.print("[bold yellow]Current State[/bold yellow]")

    state_table = Table(show_header=False, box=None)
    state_table.add_column("Metric", style="cyan", width=20)
    state_table.add_column("Value")

    state_table.add_row("Price", f"{current['price'] * 100:.1f}%")

    vol = current['volume']
    if vol >= 1_000_000:
        vol_str = f"${vol/1_000_000:.1f}M"
    elif vol >= 1_000:
        vol_str = f"${vol/1_000:.0f}K"
    else:
        vol_str = f"${vol:.0f}"
    state_table.add_row("Volume", vol_str)

    liq = current['liquidity']
    if liq >= 1_000_000:
        liq_str = f"${liq/1_000_000:.1f}M"
    elif liq >= 1_000:
        liq_str = f"${liq/1_000:.0f}K"
    else:
        liq_str = f"${liq:.0f}"
    state_table.add_row("Liquidity", liq_str)

    if current['days_remaining'] is not None:
        if current['days_remaining'] < 0:
            days_str = "[red]Expired[/red]"
        elif current['days_remaining'] == 0:
            days_str = "[yellow]Today[/yellow]"
        else:
            days_str = f"{current['days_remaining']} days"
        state_table.add_row("Time Remaining", days_str)

    console.print(state_table)
    console.print()

    # Price analysis
    console.print(f"[bold yellow]Price Analysis (Last {hours}h)[/bold yellow]")

    change_color = "green" if price_analysis['change_pct'] >= 0 else "red"

    price_table = Table(show_header=False, box=None)
    price_table.add_column("Metric", style="cyan", width=20)
    price_table.add_column("Value")

    price_table.add_row(
        "Change",
        f"[{change_color}]{price_analysis['change'] * 100:+.1f}% ({price_analysis['change_pct']:+.1f}%)[/{change_color}]"
    )
    price_table.add_row("High", f"[green]{price_analysis['high'] * 100:.1f}%[/green]")
    price_table.add_row("Low", f"[red]{price_analysis['low'] * 100:.1f}%[/red]")
    price_table.add_row("Range", f"{price_analysis['range'] * 100:.1f}%")

    console.print(price_table)
    console.print()

    # Volatility & Trend
    console.print("[bold yellow]Volatility & Trend[/bold yellow]")

    vol_color = "red" if volatility['level'] == 'High' else "yellow" if volatility['level'] == 'Medium' else "green"
    trend_color = "green" if trend['direction'] == 'Up' else "red" if trend['direction'] == 'Down' else "dim"

    vt_table = Table(show_header=False, box=None)
    vt_table.add_column("Metric", style="cyan", width=20)
    vt_table.add_column("Value")

    vt_table.add_row("Volatility", f"[{vol_color}]{volatility['level']}[/{vol_color}] ({volatility['std_dev']:.1f}%)")
    vt_table.add_row("Trend", f"[{trend_color}]{trend['direction']}[/{trend_color}] ({trend['daily_change_est']:+.2f}%/day)")
    vt_table.add_row("Momentum", trend['direction'])

    console.print(vt_table)
    console.print()

    # Technical indicators
    console.print("[bold yellow]Technical Indicators[/bold yellow]")

    rsi = technical['rsi']
    rsi_color = "red" if rsi > 70 else "green" if rsi < 30 else "cyan"

    tech_table = Table(show_header=False, box=None)
    tech_table.add_column("Metric", style="cyan", width=20)
    tech_table.add_column("Value")

    tech_table.add_row("RSI (14)", f"[{rsi_color}]{rsi:.0f}[/{rsi_color}] ({technical['rsi_signal']})")
    tech_table.add_row("Momentum", technical['momentum'].capitalize())

    console.print(tech_table)
    console.print()

    # Sparkline if we have data
    if snapshots and len(snapshots) >= 2:
        prices = [s.probability for s in reversed(snapshots)]
        chart = ASCIIChart()
        spark = chart.generate_sparkline(prices, width=40)
        console.print(f"[bold yellow]Price History[/bold yellow]")
        console.print(f"  {spark}")
        console.print(f"  [dim]{len(prices)} data points over {hours}h[/dim]")
        console.print()

    # Interpretation
    console.print("[bold yellow]Interpretation[/bold yellow]")
    interpretations = []

    if health['certainty'] > 80:
        interpretations.append("Market shows high consensus - price is near extremes")
    elif health['certainty'] < 30:
        interpretations.append("Market is uncertain - price near 50%")

    if volatility['level'] == 'High':
        interpretations.append("High volatility - expect large price swings")
    elif volatility['level'] == 'Low':
        interpretations.append("Low volatility - market is stable")

    if technical['rsi_signal'] == 'Overbought':
        interpretations.append("RSI suggests market may be overbought - potential pullback")
    elif technical['rsi_signal'] == 'Oversold':
        interpretations.append("RSI suggests market may be oversold - potential bounce")

    if trend['direction'] == 'Up' and trend['strength'] > 1:
        interpretations.append("Strong upward trend")
    elif trend['direction'] == 'Down' and trend['strength'] > 1:
        interpretations.append("Strong downward trend")

    if current['days_remaining'] is not None and current['days_remaining'] <= 3:
        interpretations.append("Approaching resolution - expect volatility and liquidity changes")

    if interpretations:
        for i, interp in enumerate(interpretations, 1):
            console.print(f"  [dim]{i}. {interp}[/dim]")
    else:
        console.print("  [dim]No significant signals detected[/dim]")

    console.print()
