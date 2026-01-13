"""Watchdog - Continuous monitoring with custom conditions"""

import click
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", multiple=True, help="Markets to watch (can specify multiple)")
@click.option("--above", "-a", type=float, default=None, help="Alert when price goes above")
@click.option("--below", "-b", type=float, default=None, help="Alert when price goes below")
@click.option("--change", "-c", type=float, default=None, help="Alert on price change (e.g., 0.05 for 5%)")
@click.option("--volume", "-v", type=float, default=None, help="Alert when 24h volume exceeds")
@click.option("--interval", "-i", type=int, default=30, help="Check interval in seconds")
@click.option("--duration", "-d", type=int, default=0, help="Duration in minutes (0 = until stopped)")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def watchdog(ctx, market, above, below, change, volume, interval, duration, output_format):
    """Continuous monitoring with custom alert conditions

    Watch markets and alert when conditions are met.
    Runs until stopped (Ctrl+C) or duration expires.

    Examples:
        polyterm watchdog -m "bitcoin" --above 0.70
        polyterm watchdog -m "trump" --below 0.40
        polyterm watchdog -m "btc" -m "eth" --change 0.05
        polyterm watchdog -m "election" --volume 100000
    """
    console = Console()
    config = ctx.obj["config"]

    if not market:
        console.print()
        console.print(Panel("[bold]Watchdog Monitor[/bold]", border_style="cyan"))
        console.print()
        console.print("Continuous monitoring with custom conditions.")
        console.print()
        console.print("Examples:")
        console.print("  [cyan]polyterm watchdog -m 'bitcoin' --above 0.70[/cyan]")
        console.print("  [cyan]polyterm watchdog -m 'trump' --below 0.40[/cyan]")
        console.print("  [cyan]polyterm watchdog -m 'btc' --change 0.05[/cyan]")
        console.print()
        return

    # Build conditions
    conditions = []
    if above:
        conditions.append({'type': 'above', 'value': above})
    if below:
        conditions.append({'type': 'below', 'value': below})
    if change:
        conditions.append({'type': 'change', 'value': change})
    if volume:
        conditions.append({'type': 'volume', 'value': volume})

    if not conditions:
        conditions.append({'type': 'any', 'value': 0.03})  # Default: 3% change

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Find markets
        watched_markets = []
        for m in market:
            markets = gamma_client.search_markets(m, limit=1)
            if markets:
                mkt = markets[0]
                watched_markets.append({
                    'market': mkt,
                    'title': mkt.get('question', mkt.get('title', ''))[:40],
                    'market_id': mkt.get('id', mkt.get('condition_id', '')),
                    'initial_price': _get_price(mkt),
                    'last_price': _get_price(mkt),
                    'last_volume': mkt.get('volume24hr', 0) or 0,
                    'alerts': [],
                })
            else:
                console.print(f"[yellow]Market not found: {m}[/yellow]")

        if not watched_markets:
            console.print("[red]No valid markets to watch.[/red]")
            return

        # Start monitoring
        _run_watchdog(console, gamma_client, watched_markets, conditions, interval, duration, output_format)

    except KeyboardInterrupt:
        console.print("\n[yellow]Watchdog stopped.[/yellow]")

    finally:
        gamma_client.close()


def _run_watchdog(console: Console, gamma_client: GammaClient, watched_markets: list, conditions: list, interval: int, duration: int, output_format: str):
    """Run the watchdog monitoring loop"""
    start_time = time.time()
    end_time = start_time + (duration * 60) if duration > 0 else float('inf')

    console.print()
    console.print(Panel("[bold]Watchdog Active[/bold]", border_style="green"))
    console.print()

    console.print(f"[bold]Watching:[/bold] {len(watched_markets)} market(s)")
    console.print(f"[bold]Conditions:[/bold] {_describe_conditions(conditions)}")
    console.print(f"[bold]Interval:[/bold] {interval}s")
    if duration > 0:
        console.print(f"[bold]Duration:[/bold] {duration} minutes")
    console.print()
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()

    check_count = 0

    while time.time() < end_time:
        check_count += 1
        check_time = datetime.now().strftime("%H:%M:%S")

        console.print(f"[dim]Check #{check_count} at {check_time}[/dim]")

        # Check each market
        for wm in watched_markets:
            try:
                # Refresh market data
                markets = gamma_client.search_markets(wm['market_id'], limit=1)
                if not markets:
                    continue

                market = markets[0]
                current_price = _get_price(market)
                current_volume = market.get('volume24hr', 0) or 0

                # Check conditions
                triggered = _check_conditions(wm, current_price, current_volume, conditions)

                if triggered:
                    for alert in triggered:
                        _display_alert(console, wm['title'], alert, output_format)
                        wm['alerts'].append({
                            'time': check_time,
                            'alert': alert,
                        })

                # Update tracked values
                wm['last_price'] = current_price
                wm['last_volume'] = current_volume

            except Exception as e:
                console.print(f"[red]Error checking {wm['title']}: {e}[/red]")

        # Wait for next check
        try:
            time.sleep(interval)
        except KeyboardInterrupt:
            break

    # Summary
    console.print()
    console.print("[bold]Watchdog Summary:[/bold]")
    total_alerts = sum(len(wm['alerts']) for wm in watched_markets)
    console.print(f"  Checks: {check_count}")
    console.print(f"  Alerts: {total_alerts}")
    console.print()


def _check_conditions(wm: dict, current_price: float, current_volume: float, conditions: list) -> list:
    """Check if any conditions are triggered"""
    triggered = []

    initial_price = wm['initial_price']
    last_price = wm['last_price']

    for cond in conditions:
        cond_type = cond['type']
        value = cond['value']

        if cond_type == 'above':
            if current_price >= value and last_price < value:
                triggered.append({
                    'type': 'above',
                    'message': f"Price crossed above {value:.0%}",
                    'price': current_price,
                })

        elif cond_type == 'below':
            if current_price <= value and last_price > value:
                triggered.append({
                    'type': 'below',
                    'message': f"Price crossed below {value:.0%}",
                    'price': current_price,
                })

        elif cond_type == 'change':
            price_change = abs(current_price - last_price)
            if price_change >= value:
                direction = "up" if current_price > last_price else "down"
                triggered.append({
                    'type': 'change',
                    'message': f"Price moved {direction} {price_change:.1%}",
                    'price': current_price,
                })

        elif cond_type == 'volume':
            if current_volume >= value and wm['last_volume'] < value:
                triggered.append({
                    'type': 'volume',
                    'message': f"24h volume exceeded ${value:,.0f}",
                    'volume': current_volume,
                })

        elif cond_type == 'any':
            price_change = abs(current_price - last_price)
            if price_change >= value:
                direction = "up" if current_price > last_price else "down"
                triggered.append({
                    'type': 'any',
                    'message': f"Price moved {direction} {price_change:.1%}",
                    'price': current_price,
                })

    return triggered


def _display_alert(console: Console, title: str, alert: dict, output_format: str):
    """Display an alert"""
    if output_format == 'json':
        print_json({
            'alert': True,
            'market': title,
            'type': alert['type'],
            'message': alert['message'],
            'timestamp': datetime.now().isoformat(),
        })
    else:
        console.print()
        console.print(f"[bold yellow]🔔 ALERT[/bold yellow]")
        console.print(f"[bold]{title}[/bold]")
        console.print(f"[cyan]{alert['message']}[/cyan]")
        if 'price' in alert:
            console.print(f"[dim]Current: {alert['price']:.1%}[/dim]")
        console.print()


def _describe_conditions(conditions: list) -> str:
    """Describe conditions in human-readable format"""
    parts = []
    for cond in conditions:
        if cond['type'] == 'above':
            parts.append(f"price > {cond['value']:.0%}")
        elif cond['type'] == 'below':
            parts.append(f"price < {cond['value']:.0%}")
        elif cond['type'] == 'change':
            parts.append(f"change >= {cond['value']:.1%}")
        elif cond['type'] == 'volume':
            parts.append(f"volume > ${cond['value']:,.0f}")
        elif cond['type'] == 'any':
            parts.append(f"any change >= {cond['value']:.1%}")

    return ", ".join(parts) if parts else "any significant change"


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
