"""Digest - Daily/weekly summary of your trading and market activity"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--period", "-p", type=click.Choice(["today", "yesterday", "week", "month"]), default="today", help="Summary period")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def digest(ctx, period, output_format):
    """Get a summary of trading and market activity

    Quick catch-up on what happened while you were away.
    Includes your P&L, market movers, and upcoming events.

    Examples:
        polyterm digest                  # Today's summary
        polyterm digest --period week    # Weekly summary
        polyterm digest --period yesterday  # Yesterday's recap
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Calculate date range
    now = datetime.now()
    if period == 'today':
        start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Today"
    elif period == 'yesterday':
        start_date = (now - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
        period_label = "Yesterday"
    elif period == 'week':
        start_date = now - timedelta(days=7)
        period_label = "This Week"
    else:
        start_date = now - timedelta(days=30)
        period_label = "This Month"

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Building digest...", total=None)

            # Get portfolio data
            portfolio_summary = _get_portfolio_summary(db, start_date)

            # Get market highlights
            market_highlights = _get_market_highlights(gamma_client)

            # Get upcoming resolutions
            upcoming = _get_upcoming_resolutions(gamma_client)

            # Get alerts summary
            alerts_summary = _get_alerts_summary(db, start_date)

    finally:
        gamma_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'period': period,
            'portfolio': portfolio_summary,
            'market_highlights': market_highlights,
            'upcoming_resolutions': upcoming,
            'alerts': alerts_summary,
        })
        return

    # Display digest
    console.print()
    console.print(Panel(f"[bold]Digest: {period_label}[/bold]\n{now.strftime('%A, %B %d, %Y')}", border_style="cyan"))
    console.print()

    # Portfolio Summary
    console.print("[bold cyan]Your Portfolio[/bold cyan]")
    console.print()

    if portfolio_summary['has_activity']:
        pnl = portfolio_summary['pnl']
        pnl_color = "green" if pnl >= 0 else "red"

        summary_table = Table(show_header=False, box=None, padding=(0, 2))
        summary_table.add_column(width=18)
        summary_table.add_column(justify="right", width=15)

        summary_table.add_row("P&L", f"[{pnl_color}]${pnl:+,.2f}[/{pnl_color}]")
        summary_table.add_row("Trades Closed", str(portfolio_summary['trades_closed']))
        summary_table.add_row("Win Rate", f"{portfolio_summary['win_rate']:.0%}")
        summary_table.add_row("Open Positions", str(portfolio_summary['open_positions']))

        console.print(summary_table)
    else:
        console.print("[dim]No trading activity in this period[/dim]")

    console.print()

    # Market Highlights
    console.print("[bold cyan]Market Highlights[/bold cyan]")
    console.print()

    if market_highlights['movers']:
        movers_table = Table(show_header=False, box=None, padding=(0, 1))
        movers_table.add_column(width=3)
        movers_table.add_column(max_width=40)
        movers_table.add_column(width=10, justify="right")

        for mover in market_highlights['movers'][:5]:
            if mover['change'] > 0:
                icon = "[green]↑[/green]"
                change_str = f"[green]+{mover['change']:.0%}[/green]"
            else:
                icon = "[red]↓[/red]"
                change_str = f"[red]{mover['change']:.0%}[/red]"

            movers_table.add_row(icon, mover['title'][:38], change_str)

        console.print(movers_table)
    else:
        console.print("[dim]No major movers[/dim]")

    console.print()

    # High Volume
    if market_highlights['high_volume']:
        console.print("[bold]High Volume:[/bold]")
        for market in market_highlights['high_volume'][:3]:
            console.print(f"  [yellow]•[/yellow] {market['title'][:45]} (${market['volume']:,.0f})")
        console.print()

    # Upcoming Resolutions
    console.print("[bold cyan]Upcoming Resolutions[/bold cyan]")
    console.print()

    if upcoming:
        for event in upcoming[:5]:
            days_label = f"in {event['days']} days" if event['days'] > 1 else "tomorrow" if event['days'] == 1 else "today"
            console.print(f"  [yellow]•[/yellow] {event['title'][:45]} ({days_label})")
    else:
        console.print("[dim]No upcoming resolutions this week[/dim]")

    console.print()

    # Alerts Summary
    if alerts_summary['count'] > 0:
        console.print("[bold cyan]Alerts[/bold cyan]")
        console.print()
        console.print(f"  [yellow]{alerts_summary['count']}[/yellow] alerts triggered")
        if alerts_summary['types']:
            types_str = ", ".join(f"{k}: {v}" for k, v in alerts_summary['types'].items())
            console.print(f"  [dim]{types_str}[/dim]")
        console.print()

    # Quick Actions
    console.print("[bold]Quick Actions:[/bold]")
    console.print("  [cyan]polyterm pin --refresh[/cyan] - Update pinned markets")
    console.print("  [cyan]polyterm signals --scan[/cyan] - Scan for opportunities")
    console.print("  [cyan]polyterm hot[/cyan] - See biggest movers")
    console.print()


def _get_portfolio_summary(db: Database, start_date: datetime) -> dict:
    """Get portfolio summary for period"""
    # Get closed positions
    positions = db.get_positions(status='closed')

    pnl = 0
    trades_closed = 0
    wins = 0

    for pos in positions:
        try:
            exit_date = datetime.fromisoformat(pos['exit_date'])
            if exit_date >= start_date:
                entry = pos.get('entry_price', 0)
                exit_price = pos.get('exit_price', 0)
                shares = pos.get('shares', 0)
                side = pos.get('side', 'yes')

                if side == 'yes':
                    trade_pnl = (exit_price - entry) * shares
                else:
                    trade_pnl = (entry - exit_price) * shares

                pnl += trade_pnl
                trades_closed += 1
                if trade_pnl > 0:
                    wins += 1
        except Exception:
            continue

    # Get open positions
    open_positions = len(db.get_positions(status='open'))

    return {
        'has_activity': trades_closed > 0,
        'pnl': pnl,
        'trades_closed': trades_closed,
        'win_rate': wins / trades_closed if trades_closed > 0 else 0,
        'open_positions': open_positions,
    }


def _get_market_highlights(gamma_client: GammaClient) -> dict:
    """Get market highlights"""
    try:
        markets = gamma_client.get_markets(limit=50, active=True)

        # Find movers
        movers = []
        high_volume = []

        for market in markets:
            title = market.get('question', market.get('title', ''))

            # Price change
            change = float(market.get('priceChange24h', 0) or 0)
            if not change:
                current = _get_price(market)
                prev = market.get('price24hAgo', 0)
                try:
                    prev = float(prev) if prev else 0
                except (ValueError, TypeError):
                    prev = 0
                if prev > 0:
                    change = (current - prev) / prev

            if abs(change) > 0.03:
                movers.append({
                    'title': title,
                    'change': change,
                })

            # Volume
            volume = market.get('volume24hr', market.get('volume24h', 0)) or 0
            if volume > 50000:
                high_volume.append({
                    'title': title,
                    'volume': volume,
                })

        # Sort
        movers.sort(key=lambda x: abs(x['change']), reverse=True)
        high_volume.sort(key=lambda x: x['volume'], reverse=True)

        return {
            'movers': movers[:10],
            'high_volume': high_volume[:5],
        }

    except Exception:
        return {'movers': [], 'high_volume': []}


def _get_upcoming_resolutions(gamma_client: GammaClient) -> list:
    """Get upcoming market resolutions"""
    try:
        markets = gamma_client.get_markets(limit=100, active=True)

        upcoming = []
        now = datetime.now()

        for market in markets:
            end_date_str = market.get('endDate', market.get('end_date', ''))
            if not end_date_str:
                continue

            try:
                # Parse date
                if 'T' in end_date_str:
                    end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                else:
                    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

                # Make naive for comparison
                if end_date.tzinfo:
                    end_date = end_date.replace(tzinfo=None)

                days_until = (end_date - now).days

                if 0 <= days_until <= 7:
                    upcoming.append({
                        'title': market.get('question', market.get('title', '')),
                        'days': days_until,
                        'date': end_date.strftime('%m/%d'),
                    })
            except Exception:
                continue

        upcoming.sort(key=lambda x: x['days'])
        return upcoming[:10]

    except Exception:
        return []


def _get_alerts_summary(db: Database, start_date: datetime) -> dict:
    """Get alerts summary for period"""
    try:
        alerts = db.get_alerts(limit=100)

        count = 0
        types = {}

        for alert in alerts:
            try:
                created = datetime.fromisoformat(alert.get('created_at', ''))
                if created >= start_date:
                    count += 1
                    alert_type = alert.get('type', 'unknown')
                    types[alert_type] = types.get(alert_type, 0) + 1
            except Exception:
                continue

        return {
            'count': count,
            'types': types,
        }
    except Exception:
        return {'count': 0, 'types': {}}


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
