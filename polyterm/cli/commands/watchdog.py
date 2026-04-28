"""Watchdog - Continuous monitoring with custom conditions"""

import click
import time
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error


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

    check_count = 0
    last_check = "waiting"
    recent_alerts = []

    def run_check():
        nonlocal check_count, last_check, recent_alerts
        check_count += 1
        check_time = datetime.now().strftime("%H:%M:%S")
        last_check = check_time

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
                        if output_format == 'json':
                            _display_alert(console, wm['title'], alert, output_format)
                        else:
                            recent_alerts.insert(0, {
                                'time': check_time,
                                'market': wm['title'],
                                'alert': alert,
                            })
                            recent_alerts = recent_alerts[:8]
                        wm['alerts'].append({
                            'time': check_time,
                            'alert': alert,
                        })

                # Update tracked values
                wm['last_price'] = current_price
                wm['last_volume'] = current_volume

            except Exception as e:
                if output_format == 'json':
                    handle_api_error(console, e, f"checking {wm['title']}")
                else:
                    recent_alerts.insert(0, {
                        'time': check_time,
                        'market': wm['title'],
                        'alert': {
                            'type': 'error',
                            'message': str(e),
                        },
                    })
                    recent_alerts = recent_alerts[:8]

    if output_format == 'json':
        while time.time() < end_time:
            run_check()
            try:
                time.sleep(interval)
            except KeyboardInterrupt:
                break
    else:
        with Live(
            _render_watchdog_dashboard(
                watched_markets,
                conditions,
                interval,
                duration,
                start_time,
                check_count,
                last_check,
                recent_alerts,
            ),
            console=console,
            refresh_per_second=1,
            screen=True,
        ) as live:
            while time.time() < end_time:
                run_check()
                live.update(_render_watchdog_dashboard(
                    watched_markets,
                    conditions,
                    interval,
                    duration,
                    start_time,
                    check_count,
                    last_check,
                    recent_alerts,
                ))

                try:
                    time.sleep(interval)
                except KeyboardInterrupt:
                    break

    total_alerts = sum(len(wm['alerts']) for wm in watched_markets)

    # Summary
    if output_format != 'json':
        console.print()
        console.print("[bold]Watchdog Summary:[/bold]")
        console.print(f"  Checks: {check_count}")
        console.print(f"  Alerts: {total_alerts}")
        console.print()


def _render_watchdog_dashboard(
    watched_markets: list,
    conditions: list,
    interval: int,
    duration: int,
    start_time: float,
    check_count: int,
    last_check: str,
    recent_alerts: list,
) -> Layout:
    """Render the fixed watchdog dashboard."""
    elapsed = int(time.time() - start_time)
    elapsed_text = f"{elapsed // 60}m {elapsed % 60}s"
    duration_text = "until stopped" if duration <= 0 else f"{duration}m"
    total_alerts = sum(len(wm['alerts']) for wm in watched_markets)

    header = Panel(
        Text.from_markup(
            "[bold green]Watchdog Active[/bold green]\n"
            f"Watching: [cyan]{len(watched_markets)} market(s)[/cyan] | "
            f"Conditions: [white]{_describe_conditions(conditions)}[/white]\n"
            f"Checks: [cyan]{check_count}[/cyan] | "
            f"Alerts: [yellow]{total_alerts}[/yellow] | "
            f"Last check: [white]{last_check}[/white] | "
            f"Interval: [white]{interval}s[/white] | "
            f"Elapsed: [white]{elapsed_text}[/white] | Duration: [white]{duration_text}[/white]\n"
            "[dim]Press Ctrl+C to stop[/dim]"
        ),
        border_style="green",
        padding=(0, 2),
    )

    market_table = Table(
        title="Watched Markets",
        title_style="bold cyan",
        expand=True,
    )
    market_table.add_column("Market", style="white", ratio=1, overflow="ellipsis")
    market_table.add_column("Price", justify="right", width=10)
    market_table.add_column("Initial", justify="right", width=10)
    market_table.add_column("Change", justify="right", width=10)
    market_table.add_column("24h Volume", justify="right", width=14)
    market_table.add_column("Alerts", justify="right", width=8)

    for wm in watched_markets:
        current_price = float(wm.get('last_price', 0) or 0)
        initial_price = float(wm.get('initial_price', 0) or 0)
        price_change = current_price - initial_price
        change_style = "green" if price_change > 0 else "red" if price_change < 0 else "yellow"
        market_table.add_row(
            wm.get('title', 'Unknown'),
            f"{current_price:.1%}",
            f"{initial_price:.1%}",
            f"[{change_style}]{price_change:+.1%}[/{change_style}]",
            f"${float(wm.get('last_volume', 0) or 0):,.0f}",
            str(len(wm.get('alerts', []))),
        )

    alerts_table = Table(
        title="Recent Alerts",
        title_style="bold yellow",
        expand=True,
    )
    alerts_table.add_column("Time", style="dim", width=8)
    alerts_table.add_column("Market", style="white", ratio=1, overflow="ellipsis")
    alerts_table.add_column("Condition", style="cyan", ratio=1, overflow="ellipsis")

    if recent_alerts:
        for item in recent_alerts:
            alert = item['alert']
            style = "red" if alert.get('type') == 'error' else "yellow"
            alerts_table.add_row(
                item['time'],
                item['market'],
                Text(alert.get('message', ''), style=style),
            )
    else:
        alerts_table.add_row("--:--:--", "No alerts yet", Text("Waiting", style="dim"))

    layout = Layout()
    layout.split_column(
        Layout(header, size=7),
        Layout(market_table, ratio=2),
        Layout(alerts_table, ratio=1),
    )
    return layout


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
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)
