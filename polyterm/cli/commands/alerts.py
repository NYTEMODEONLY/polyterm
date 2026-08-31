"""Alerts command - manage and view alerts"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...api.data_api_lag import DISCLOSURE, label_payload, table_title
from ...db.database import Database
from ...core.alert_engine import AlertEngine
from ...core.notifications import NotificationConfig, NotificationManager
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error


@click.command()
@click.option("--type", "alert_type", type=click.Choice(["all", "whale", "insider", "arbitrage", "smart_money", "print"]), default="all", help="Filter by alert type")
@click.option("--limit", default=20, help="Maximum alerts to show, or max matching prints when evaluating")
@click.option("--unread", is_flag=True, help="Show only unacknowledged alerts")
@click.option("--ack", default=None, type=int, help="Acknowledge alert by ID")
@click.option(
    "--add-rule",
    type=click.Choice(["price", "print"]),
    default=None,
    help="Create a local alert rule (price: Gamma probability; print: lagged Data API fill, not live CLOB)",
)
@click.option("--evaluate", type=click.Choice(["price", "print"]), default=None, help="Evaluate a rule once without requiring a saved rule")
@click.option("--market", default=None, help="Market for a price rule, or optional market filter for a print rule")
@click.option("--above", type=float, default=None, help="Trigger price rule at or above this probability")
@click.option("--below", type=float, default=None, help="Trigger price rule at or below this probability")
@click.option("--min-notional", type=float, default=None, help="Minimum verified-print notional for a print rule")
@click.option("--wallet", default=None, help="Optional wallet filter for a print rule")
@click.option("--dry-run", is_flag=True, help="Preview rule creation or evaluation without mutating local state")
@click.option("--test-telegram", is_flag=True, help="Send test Telegram notification")
@click.option("--test-discord", is_flag=True, help="Send test Discord notification")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def alerts(ctx, alert_type, limit, unread, ack, add_rule, evaluate, market, above, below, min_notional, wallet, dry_run, test_telegram, test_discord, output_format):
    """View and manage alerts.

    Print rules fire on verified Data API fills (lagged, not live CLOB).
    """

    config = ctx.obj["config"]
    console = Console()
    db = Database()

    try:
        if add_rule:
            engine = AlertEngine(database=db)
            _handle_add_rule(
                console=console,
                engine=engine,
                add_rule=add_rule,
                market=market,
                above=above,
                below=below,
                min_notional=min_notional,
                wallet=wallet,
                dry_run=dry_run,
                output_format=output_format,
            )
            return

        if evaluate:
            engine = AlertEngine(database=db)
            _handle_evaluate(
                console=console,
                engine=engine,
                evaluate=evaluate,
                market=market,
                above=above,
                below=below,
                min_notional=min_notional,
                wallet=wallet,
                limit=limit,
                dry_run=dry_run,
                output_format=output_format,
            )
            return

        # Handle acknowledgment
        if ack:
            db.acknowledge_alert(ack)
            if output_format == 'json':
                print_json({'success': True, 'action': 'acknowledged', 'alert_id': ack})
            else:
                console.print(f"[green]Alert {ack} acknowledged[/green]")
            return

        # Test notifications
        if test_telegram or test_discord:
            notif_config = NotificationConfig.from_dict(config.notification_config)
            manager = NotificationManager(notif_config)

            if test_telegram:
                result = manager.test_telegram()
                if output_format == 'json':
                    print_json({'success': result, 'channel': 'telegram'})
                else:
                    if result:
                        console.print("[green]Telegram test notification sent successfully![/green]")
                    else:
                        console.print("[red]Telegram test failed. Check your bot_token and chat_id.[/red]")

            if test_discord:
                result = manager.test_discord()
                if output_format == 'json':
                    print_json({'success': result, 'channel': 'discord'})
                else:
                    if result:
                        console.print("[green]Discord test notification sent successfully![/green]")
                    else:
                        console.print("[red]Discord test failed. Check your webhook_url.[/red]")
            return

        # Get alerts
        if unread:
            alerts_list = db.get_unacknowledged_alerts(limit=limit)
        elif alert_type != "all":
            alerts_list = db.get_recent_alerts(limit=limit, alert_type=alert_type)
        else:
            alerts_list = db.get_recent_alerts(limit=limit)

        has_print_alerts = any(getattr(item, "alert_type", "") == "print" for item in alerts_list)

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'filter': alert_type,
                'unread_only': unread,
                'count': len(alerts_list),
                'alerts': [a.to_dict() for a in alerts_list],
            }
            if has_print_alerts or alert_type == "print":
                output = label_payload(output, quality_flags=output.get("quality_flags") or [])
            print_json(output)
            return

        if not alerts_list:
            if alert_type == "print":
                console.print(Panel("[yellow]{}[/yellow]".format(DISCLOSURE), border_style="yellow"))
            console.print("[yellow]No alerts found[/yellow]")
            return

        if has_print_alerts or alert_type == "print":
            console.print(Panel("[yellow]{}[/yellow]".format(DISCLOSURE), border_style="yellow"))
            title = table_title("Recent Alerts")
        else:
            title = "Recent Alerts"

        # Create table
        table = Table(title=title)

        table.add_column("ID", style="dim")
        table.add_column("Type", style="cyan")
        table.add_column("Severity", justify="center")
        table.add_column("Message", max_width=40)
        table.add_column("Time", style="dim")
        table.add_column("Status", justify="center")

        for alert in alerts_list:
            # Severity color
            if alert.severity >= 70:
                sev_color = "red"
                sev_display = "HIGH"
            elif alert.severity >= 40:
                sev_color = "yellow"
                sev_display = "MED"
            else:
                sev_color = "green"
                sev_display = "LOW"

            # Status
            status = "[dim]read[/dim]" if alert.acknowledged else "[bold green]NEW[/bold green]"

            # Time ago
            time_diff = datetime.now() - alert.created_at
            if time_diff.days > 0:
                time_ago = f"{time_diff.days}d ago"
            elif time_diff.seconds >= 3600:
                time_ago = f"{time_diff.seconds // 3600}h ago"
            else:
                time_ago = f"{time_diff.seconds // 60}m ago"

            table.add_row(
                str(alert.id),
                alert.alert_type,
                f"[{sev_color}]{sev_display}[/{sev_color}]",
                alert.message[:40],
                time_ago,
                status,
            )

        console.print(table)

        # Unread count
        unread_count = len([a for a in alerts_list if not a.acknowledged])
        if unread_count > 0:
            console.print(f"\n[bold]{unread_count} unread alerts[/bold]")
            console.print("[dim]Use --ack <ID> to acknowledge an alert[/dim]")

        # Notification config status
        notif_config = config.notification_config
        enabled = []
        if notif_config.get('telegram', {}).get('enabled'):
            enabled.append('Telegram')
        if notif_config.get('discord', {}).get('enabled'):
            enabled.append('Discord')
        if notif_config.get('system', {}).get('enabled'):
            enabled.append('System')

        if enabled:
            console.print(f"\n[dim]Notifications enabled: {', '.join(enabled)}[/dim]")
        else:
            console.print(f"\n[dim]No external notifications configured. Use 'polyterm config' to set up.[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            handle_api_error(console, e, "alerts")


def _handle_add_rule(console, engine, add_rule, market, above, below, min_notional, wallet, dry_run, output_format):
    if add_rule == "print":
        if min_notional is None:
            _rule_error(console, output_format, "--min-notional is required for --add-rule print")
            return
        result = engine.create_print_rule(
            min_notional=min_notional,
            market=market,
            wallet=wallet,
            dry_run=dry_run,
        )
        if output_format == "json":
            print_json({"success": True, **result})
            return
        action = "Previewed" if dry_run else "Created"
        console.print(Panel("[yellow]{}[/yellow]".format(DISCLOSURE), border_style="yellow"))
        console.print("[green]{} print alert rule (min notional ${:,.0f})[/green]".format(
            action, float(min_notional)
        ))
        return

    if not market:
        _rule_error(console, output_format, "--market is required for --add-rule price")
        return
    result = engine.create_price_rule(
        market=market,
        above=above,
        below=below,
        dry_run=dry_run,
    )
    if output_format == "json":
        print_json({"success": True, **result})
        return
    action = "Previewed" if dry_run else "Created"
    console.print("[green]{} price alert rule for {}[/green]".format(
        action, result["rule"]["title"]
    ))


def _handle_evaluate(console, engine, evaluate, market, above, below, min_notional, wallet, limit, dry_run, output_format):
    if evaluate == "print":
        if min_notional is None:
            _rule_error(console, output_format, "--min-notional is required for --evaluate print")
            return
        result = engine.run_print_once(
            min_notional=min_notional,
            market=market,
            wallet=wallet,
            limit=limit,
            dry_run=dry_run,
        )
        if output_format == "json":
            print_json({"success": True, **result})
            return
        console.print(Panel("[yellow]{}[/yellow]".format(DISCLOSURE), border_style="yellow"))
        title = table_title("Verified prints")
        table = Table(title=title)
        table.add_column("Time", style="dim")
        table.add_column("Market", style="cyan")
        table.add_column("Wallet", style="white")
        table.add_column("Side", justify="center")
        table.add_column("Notional", justify="right", style="yellow")
        prints = result.get("prints") or []
        if not prints:
            console.print("[yellow]No verified prints matched this rule[/yellow]")
            console.print("[dim]Empty Data API tape is not invented fills. source=data_api lagged=true[/dim]")
            return
        for row in prints:
            table.add_row(
                str(row.get("timestamp_iso") or row.get("timestamp") or "unknown"),
                str(row.get("market_title") or row.get("market_slug") or row.get("market_id") or row.get("condition_id") or "unknown"),
                str(row.get("wallet") or "unknown"),
                str(row.get("side") or "unknown"),
                _format_notional(row.get("notional")),
            )
        console.print(table)
        action = "Would store" if dry_run else "Stored"
        console.print("[green]{} {} print alert(s). Matched {} of {} fetched rows.[/green]".format(
            action, len(result.get("alerts") or []), result.get("matched", 0), result.get("fetched", 0)
        ))
        return

    if not market:
        _rule_error(console, output_format, "--market is required for --evaluate price")
        return
    result = engine.run_once(market=market, above=above, below=below, dry_run=dry_run)
    if output_format == "json":
        print_json({"success": True, **result})
        return
    if result.get("triggered"):
        console.print("[green]Price rule triggered: {}[/green]".format("; ".join(result.get("reasons") or [])))
    else:
        console.print("[yellow]Price rule did not trigger[/yellow]")


def _rule_error(console, output_format, message):
    if output_format == "json":
        print_json({"success": False, "error": message})
    else:
        console.print("[red]{}[/red]".format(message))


def _format_notional(value):
    if value is None:
        return "unknown"
    try:
        return "${:,.0f}".format(float(value))
    except (TypeError, ValueError):
        return "unknown"
