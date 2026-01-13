"""Price Alerts - Set alerts when markets hit target prices"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt, Confirm

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--list", "-l", "list_alerts", is_flag=True, help="List all active price alerts")
@click.option("--add", "-a", "add_market", default=None, help="Add alert for market (ID or search term)")
@click.option("--remove", "-r", "remove_id", type=int, default=None, help="Remove alert by ID")
@click.option("--check", "-c", is_flag=True, help="Check alerts against current prices")
@click.option("--all", "show_all", is_flag=True, help="Show all alerts including triggered")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def pricealert(ctx, list_alerts, add_market, remove_id, check, show_all, interactive, output_format):
    """Set price alerts for markets

    Get notified when markets reach your target prices.

    Examples:
        polyterm pricealert --list              # List active alerts
        polyterm pricealert --add "bitcoin"     # Add alert for market
        polyterm pricealert --check             # Check if any alerts triggered
        polyterm pricealert -i                  # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Remove alert
    if remove_id:
        if db.remove_price_alert(remove_id):
            if output_format == 'json':
                print_json({'success': True, 'action': 'removed', 'alert_id': remove_id})
            else:
                console.print(f"[green]Alert #{remove_id} removed.[/green]")
        else:
            if output_format == 'json':
                print_json({'success': False, 'error': f'Alert #{remove_id} not found'})
            else:
                console.print(f"[yellow]Alert #{remove_id} not found.[/yellow]")
        return

    # Check alerts
    if check:
        _check_alerts(console, config, db, output_format)
        return

    # Add alert
    if add_market:
        _add_alert_for_market(console, config, db, add_market, output_format)
        return

    # Interactive mode
    if interactive:
        _interactive_mode(console, config, db)
        return

    # List alerts (default)
    _list_alerts(console, db, show_all, output_format)


def _list_alerts(console: Console, db: Database, show_all: bool, output_format: str):
    """List price alerts"""
    alerts = db.get_price_alerts(active_only=not show_all)

    if output_format == 'json':
        print_json({
            'success': True,
            'count': len(alerts),
            'alerts': alerts,
        })
        return

    if not alerts:
        console.print("[yellow]No price alerts set.[/yellow]")
        console.print("[dim]Use 'polyterm pricealert -i' to set alerts.[/dim]")
        return

    console.print()
    console.print(Panel("[bold]Price Alerts[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Market", max_width=40)
    table.add_column("Target", justify="right", width=8)
    table.add_column("Direction", width=10)
    table.add_column("Status", width=10)
    table.add_column("Created", width=12)

    for alert in alerts:
        # Direction display
        direction = alert.get('direction', 'above')
        if direction == 'above':
            dir_str = "[green]Above[/green]"
        else:
            dir_str = "[red]Below[/red]"

        # Status display
        if alert.get('triggered'):
            status = "[yellow]Triggered[/yellow]"
        else:
            status = "[green]Active[/green]"

        # Time
        try:
            created = datetime.fromisoformat(alert['created_at'])
            time_str = created.strftime("%m/%d %H:%M")
        except Exception:
            time_str = alert.get('created_at', '')[:10]

        table.add_row(
            str(alert['id']),
            alert.get('title', '')[:38],
            f"{alert.get('target_price', 0) * 100:.0f}%",
            dir_str,
            status,
            time_str,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(alerts)} alert(s)[/dim]")
    console.print("[dim]Use 'polyterm pricealert --check' to check current prices[/dim]")
    console.print()


def _add_alert_for_market(console: Console, config, db: Database, search_term: str, output_format: str):
    """Add a price alert for a market"""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        console.print(f"[dim]Searching for: {search_term}[/dim]")
        markets = gamma_client.search_markets(search_term, limit=5)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
            else:
                console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
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
        title = selected.get('question', selected.get('title', ''))[:100]

        # Get current price
        import json
        outcome_prices = selected.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []
        current_price = float(outcome_prices[0]) if outcome_prices else 0.5

        console.print()
        console.print(f"[bold]{title}[/bold]")
        console.print(f"Current price: [cyan]{current_price * 100:.1f}%[/cyan]")
        console.print()

        # Get target price
        target_input = FloatPrompt.ask(
            "[cyan]Target price (e.g., 75 for 75%)[/cyan]",
            default=current_price * 100
        )
        target_price = target_input / 100 if target_input > 1 else target_input

        # Determine direction
        if target_price > current_price:
            direction = "above"
            console.print(f"[dim]Alert when price rises above {target_price * 100:.0f}%[/dim]")
        else:
            direction = "below"
            console.print(f"[dim]Alert when price falls below {target_price * 100:.0f}%[/dim]")

        # Optional notes
        notes = Prompt.ask("[cyan]Notes (optional)[/cyan]", default="")

        # Save alert
        alert_id = db.add_price_alert(market_id, title, target_price, direction, notes)

        if output_format == 'json':
            print_json({
                'success': True,
                'action': 'added',
                'alert_id': alert_id,
                'market_id': market_id,
                'target_price': target_price,
                'direction': direction,
            })
        else:
            console.print()
            console.print(f"[green]Alert #{alert_id} created![/green]")
            console.print(f"[dim]You'll be alerted when {title[:30]}... goes {direction} {target_price * 100:.0f}%[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _check_alerts(console: Console, config, db: Database, output_format: str):
    """Check alerts against current prices"""
    alerts = db.get_price_alerts(active_only=True)

    if not alerts:
        if output_format == 'json':
            print_json({'success': True, 'triggered': [], 'message': 'No active alerts'})
        else:
            console.print("[yellow]No active price alerts to check.[/yellow]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    triggered = []
    checked = 0

    try:
        console.print("[dim]Checking price alerts...[/dim]")
        console.print()

        for alert in alerts:
            market_id = alert['market_id']
            target = alert['target_price']
            direction = alert['direction']

            try:
                market = gamma_client.get_market(market_id)
                if not market:
                    continue

                import json
                outcome_prices = market.get('outcomePrices', [])
                if isinstance(outcome_prices, str):
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except Exception:
                        outcome_prices = []

                current_price = float(outcome_prices[0]) if outcome_prices else 0.5
                checked += 1

                # Check if triggered
                is_triggered = False
                if direction == 'above' and current_price >= target:
                    is_triggered = True
                elif direction == 'below' and current_price <= target:
                    is_triggered = True

                if is_triggered:
                    db.trigger_price_alert(alert['id'])
                    triggered.append({
                        'id': alert['id'],
                        'title': alert['title'],
                        'target': target,
                        'current': current_price,
                        'direction': direction,
                    })

                    if output_format != 'json':
                        console.print(f"[bold yellow]TRIGGERED![/bold yellow] Alert #{alert['id']}")
                        console.print(f"  {alert['title'][:50]}")
                        console.print(f"  Target: {target * 100:.0f}% ({direction})")
                        console.print(f"  Current: [cyan]{current_price * 100:.1f}%[/cyan]")
                        console.print()

            except Exception:
                continue

        if output_format == 'json':
            print_json({
                'success': True,
                'checked': checked,
                'triggered_count': len(triggered),
                'triggered': triggered,
            })
        else:
            console.print(f"[dim]Checked {checked} alert(s)[/dim]")
            if triggered:
                console.print(f"[bold yellow]{len(triggered)} alert(s) triggered![/bold yellow]")
            else:
                console.print("[green]No alerts triggered.[/green]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _interactive_mode(console: Console, config, db: Database):
    """Interactive price alert management"""
    console.print(Panel(
        "[bold]Price Alerts[/bold]\n\n"
        "[dim]Set alerts to notify you when markets hit target prices.[/dim]\n\n"
        "You can set alerts for price increases or decreases.",
        title="[cyan]Price Alerts[/cyan]",
        border_style="cyan",
    ))
    console.print()

    while True:
        console.print("[bold]Options:[/bold]")
        console.print("  [cyan]1.[/cyan] Add new price alert")
        console.print("  [cyan]2.[/cyan] View active alerts")
        console.print("  [cyan]3.[/cyan] Check alerts now")
        console.print("  [cyan]4.[/cyan] Remove an alert")
        console.print("  [cyan]q.[/cyan] Exit")
        console.print()

        choice = Prompt.ask("[cyan]Select option[/cyan]", default="q")

        if choice == '1':
            search = Prompt.ask("[cyan]Search for market[/cyan]")
            if search:
                _add_alert_for_market(console, config, db, search, "table")
        elif choice == '2':
            _list_alerts(console, db, False, "table")
        elif choice == '3':
            _check_alerts(console, config, db, "table")
        elif choice == '4':
            alerts = db.get_price_alerts(active_only=False)
            if alerts:
                _list_alerts(console, db, True, "table")
                alert_id = Prompt.ask("[cyan]Enter alert ID to remove[/cyan]", default="")
                if alert_id:
                    try:
                        if db.remove_price_alert(int(alert_id)):
                            console.print(f"[green]Alert #{alert_id} removed.[/green]")
                        else:
                            console.print("[yellow]Alert not found.[/yellow]")
                    except ValueError:
                        console.print("[red]Invalid ID.[/red]")
            else:
                console.print("[yellow]No alerts to remove.[/yellow]")
        elif choice.lower() == 'q':
            break

        console.print()
