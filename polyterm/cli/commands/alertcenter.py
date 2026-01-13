"""Alert Center - Unified view of all alerts and notifications"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...db.database import Database
from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command(name="center")
@click.option("--all", "-a", "show_all", is_flag=True, help="Show all alerts including acknowledged")
@click.option("--type", "-t", "alert_type", default=None, help="Filter by type (price, whale, resolution)")
@click.option("--clear", "-c", is_flag=True, help="Clear all alerts")
@click.option("--check", is_flag=True, help="Check for new alerts")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def center(ctx, show_all, alert_type, clear, check, output_format):
    """Unified alert center for all notifications

    View and manage all your alerts in one place:
    - Price alerts (targets hit)
    - Whale activity alerts
    - Resolution alerts (markets ending)
    - Position alerts (P&L thresholds)

    Examples:
        polyterm center                  # View active alerts
        polyterm center --all            # Include acknowledged
        polyterm center --type price     # Only price alerts
        polyterm center --check          # Check for new alerts
        polyterm center --clear          # Clear all alerts
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Clear all alerts
    if clear:
        _clear_alerts(console, db, output_format)
        return

    # Check for new alerts
    if check:
        _check_alerts(console, config, db, output_format)
        return

    # Show alerts
    _show_alerts(console, db, show_all, alert_type, output_format)


def _show_alerts(console: Console, db: Database, show_all: bool, alert_type: str, output_format: str):
    """Show all alerts"""
    # Get alerts from database
    if show_all:
        alerts = db.get_all_alerts()
    else:
        alerts = db.get_unacked_alerts()

    # Filter by type
    if alert_type:
        alerts = [a for a in alerts if alert_type.lower() in a.get('alert_type', '').lower()]

    # Also get price alerts
    price_alerts = _get_price_alerts(db)

    # Combine and sort
    all_alerts = []

    for alert in alerts:
        all_alerts.append({
            'id': alert.get('id'),
            'type': alert.get('alert_type', 'unknown'),
            'message': alert.get('message', ''),
            'severity': alert.get('severity', 0),
            'created_at': alert.get('created_at', ''),
            'acknowledged': alert.get('acknowledged', 0),
            'source': 'system',
        })

    for pa in price_alerts:
        if pa.get('triggered'):
            all_alerts.append({
                'id': f"price_{pa.get('id')}",
                'type': 'price_alert',
                'message': f"{pa.get('title', 'Market')[:30]} hit {pa.get('direction', '')} target {pa.get('target_price', 0):.0%}",
                'severity': 2,
                'created_at': pa.get('triggered_at', ''),
                'acknowledged': 0,
                'source': 'price',
            })

    # Sort by date
    all_alerts.sort(key=lambda x: x.get('created_at', ''), reverse=True)

    if output_format == 'json':
        print_json({'success': True, 'count': len(all_alerts), 'alerts': all_alerts})
        return

    console.print()
    console.print(Panel("[bold]Alert Center[/bold]", border_style="cyan"))
    console.print()

    if not all_alerts:
        console.print("[green]No active alerts.[/green]")
        console.print("[dim]Set alerts with 'polyterm pricealert' or 'polyterm alerts'[/dim]")
        return

    # Group by type
    by_type = {}
    for alert in all_alerts:
        t = alert['type']
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(alert)

    # Display each type
    type_icons = {
        'price_alert': '💰',
        'whale': '🐋',
        'resolution': '⏰',
        'position': '📊',
        'arbitrage': '💱',
    }

    for alert_type, type_alerts in by_type.items():
        icon = type_icons.get(alert_type, '🔔')
        type_label = alert_type.replace('_', ' ').title()

        console.print(f"[bold]{icon} {type_label}[/bold] ({len(type_alerts)})")
        console.print()

        for alert in type_alerts[:5]:
            # Severity color
            sev = alert.get('severity', 0)
            if sev >= 3:
                color = "red"
            elif sev >= 2:
                color = "yellow"
            else:
                color = "dim"

            # Time
            try:
                created = datetime.fromisoformat(alert['created_at'])
                age = datetime.now() - created
                if age.days > 0:
                    time_str = f"{age.days}d ago"
                elif age.seconds > 3600:
                    time_str = f"{age.seconds // 3600}h ago"
                else:
                    time_str = f"{age.seconds // 60}m ago"
            except Exception:
                time_str = ""

            ack = "[dim]✓[/dim]" if alert.get('acknowledged') else ""

            console.print(f"  [{color}]●[/{color}] {alert['message'][:50]} [dim]{time_str}[/dim] {ack}")

        if len(type_alerts) > 5:
            console.print(f"  [dim]... and {len(type_alerts) - 5} more[/dim]")

        console.print()

    # Summary
    unacked = sum(1 for a in all_alerts if not a.get('acknowledged'))
    console.print(f"[dim]Total: {len(all_alerts)} alerts ({unacked} unacknowledged)[/dim]")
    console.print()


def _check_alerts(console: Console, config, db: Database, output_format: str):
    """Check for new alerts"""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    new_alerts = []

    try:
        console.print("[dim]Checking price alerts...[/dim]")

        # Check price alerts
        price_alerts = _get_price_alerts(db)
        for pa in price_alerts:
            if pa.get('triggered'):
                continue

            # Get current price
            markets = gamma_client.search_markets(pa.get('market_id', ''), limit=1)
            if not markets:
                continue

            market = markets[0]
            current_price = _get_price(market)

            # Check if triggered
            target = pa.get('target_price', 0)
            direction = pa.get('direction', 'above')

            triggered = False
            if direction == 'above' and current_price >= target:
                triggered = True
            elif direction == 'below' and current_price <= target:
                triggered = True

            if triggered:
                # Mark as triggered
                _trigger_price_alert(db, pa['id'])
                new_alerts.append({
                    'type': 'price_alert',
                    'message': f"{pa.get('title', 'Market')[:30]} hit {direction} target {target:.0%}",
                })

        # Check resolution alerts (markets ending soon)
        console.print("[dim]Checking resolution alerts...[/dim]")
        bookmarks = db.get_bookmarks()

        for bm in bookmarks:
            markets = gamma_client.search_markets(bm.get('market_id', ''), limit=1)
            if not markets:
                continue

            market = markets[0]
            end_date_str = market.get('endDate', '')
            if not end_date_str:
                continue

            try:
                if 'T' in end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                    end_date = end_date.replace(tzinfo=None)
                else:
                    end_date = datetime.fromisoformat(end_date_str)

                days_left = (end_date - datetime.now()).days

                if 0 <= days_left <= 1:
                    new_alerts.append({
                        'type': 'resolution',
                        'message': f"Bookmarked market '{bm.get('title', '')[:30]}' resolves soon",
                    })
            except Exception:
                continue

        # Check position alerts (large P&L changes)
        console.print("[dim]Checking position alerts...[/dim]")
        positions = db.get_positions(status='open')

        for pos in positions:
            markets = gamma_client.search_markets(pos.get('market_id', ''), limit=1)
            if not markets:
                continue

            market = markets[0]
            current_price = _get_price(market)

            entry = pos.get('entry_price', 0)
            shares = pos.get('shares', 0)

            if pos.get('side') == 'yes':
                pnl_pct = (current_price - entry) / entry if entry > 0 else 0
            else:
                pnl_pct = (entry - current_price) / (1 - entry) if entry < 1 else 0

            # Alert on >20% gain or >30% loss
            if pnl_pct > 0.20:
                new_alerts.append({
                    'type': 'position',
                    'message': f"Position '{pos.get('title', '')[:25]}' up {pnl_pct:.0%}",
                })
            elif pnl_pct < -0.30:
                new_alerts.append({
                    'type': 'position',
                    'message': f"Position '{pos.get('title', '')[:25]}' down {pnl_pct:.0%}",
                })

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error checking alerts: {e}[/red]")
        return
    finally:
        gamma_client.close()

    if output_format == 'json':
        print_json({'success': True, 'new_alerts': len(new_alerts), 'alerts': new_alerts})
        return

    console.print()
    if new_alerts:
        console.print(f"[yellow]Found {len(new_alerts)} new alerts:[/yellow]")
        console.print()
        for alert in new_alerts:
            console.print(f"  [yellow]●[/yellow] [{alert['type']}] {alert['message']}")
        console.print()
    else:
        console.print("[green]No new alerts.[/green]")
        console.print()


def _clear_alerts(console: Console, db: Database, output_format: str):
    """Clear all alerts"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE alerts SET acknowledged = 1")
        cleared = cursor.rowcount

    if output_format == 'json':
        print_json({'success': True, 'cleared': cleared})
    else:
        console.print(f"[green]Cleared {cleared} alerts.[/green]")


def _get_price_alerts(db: Database) -> list:
    """Get price alerts from database"""
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM price_alerts ORDER BY created_at DESC")
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []


def _trigger_price_alert(db: Database, alert_id: int):
    """Mark price alert as triggered"""
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE price_alerts SET triggered = 1, triggered_at = ? WHERE id = ?",
                (datetime.now().isoformat(), alert_id)
            )
    except Exception:
        pass


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))
