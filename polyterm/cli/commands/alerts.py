"""Alerts command - manage and view alerts"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table

from ...db.database import Database
from ...core.notifications import NotificationConfig, NotificationManager
from ...utils.json_output import print_json


@click.command()
@click.option("--type", "alert_type", type=click.Choice(["all", "whale", "insider", "arbitrage", "smart_money"]), default="all", help="Filter by alert type")
@click.option("--limit", default=20, help="Maximum alerts to show")
@click.option("--unread", is_flag=True, help="Show only unacknowledged alerts")
@click.option("--ack", default=None, type=int, help="Acknowledge alert by ID")
@click.option("--test-telegram", is_flag=True, help="Send test Telegram notification")
@click.option("--test-discord", is_flag=True, help="Send test Discord notification")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def alerts(ctx, alert_type, limit, unread, ack, test_telegram, test_discord, output_format):
    """View and manage alerts"""

    config = ctx.obj["config"]
    console = Console()
    db = Database()

    try:
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
            print_json(output)
            return

        if not alerts_list:
            console.print("[yellow]No alerts found[/yellow]")
            return

        # Create table
        table = Table(title="Recent Alerts")

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
            console.print(f"[red]Error: {e}[/red]")
