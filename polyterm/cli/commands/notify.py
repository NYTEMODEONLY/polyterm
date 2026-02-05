"""Notification Settings Command - Configure alerts and notifications"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ...utils.config import Config
from ...utils.json_output import print_json


@click.command()
@click.option("--status", "-s", is_flag=True, help="Show notification status")
@click.option("--enable", type=click.Choice(["desktop", "sound", "webhook"]), help="Enable notification type")
@click.option("--disable", type=click.Choice(["desktop", "sound", "webhook"]), help="Disable notification type")
@click.option("--webhook", default=None, help="Set webhook URL")
@click.option("--test", "-t", is_flag=True, help="Send test notification")
@click.option("--configure", "-c", is_flag=True, help="Interactive configuration")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def notify(ctx, status, enable, disable, webhook, test, configure, output_format):
    """Configure notification settings

    Set up how you want to be notified about alerts,
    price movements, and other events.

    Notification Types:
        desktop - Desktop notifications (macOS/Windows/Linux)
        sound   - Audible alerts
        webhook - HTTP webhook (Discord, Slack, etc.)

    Examples:
        polyterm notify --status              # View settings
        polyterm notify --enable desktop      # Enable desktop
        polyterm notify --webhook "https://..." # Set webhook
        polyterm notify --test                # Test notifications
        polyterm notify -c                    # Interactive config
    """
    console = Console()
    config = Config()

    # Load current settings
    settings = _get_notification_settings(config)

    if configure:
        _interactive_configure(console, config, settings)
        return

    if status or (not enable and not disable and not webhook and not test):
        _show_status(console, settings, output_format)
        return

    if enable:
        settings[enable] = True
        _save_notification_settings(config, settings)
        console.print(f"[green]{enable.title()} notifications enabled.[/green]")

    if disable:
        settings[disable] = False
        _save_notification_settings(config, settings)
        console.print(f"[yellow]{disable.title()} notifications disabled.[/yellow]")

    if webhook:
        settings['webhook_url'] = webhook
        settings['webhook'] = True
        _save_notification_settings(config, settings)
        console.print(f"[green]Webhook URL set.[/green]")

    if test:
        _test_notifications(console, settings)


def _get_notification_settings(config: Config) -> dict:
    """Get current notification settings"""
    return {
        'desktop': config.get('notifications.desktop', True),
        'sound': config.get('notifications.sound', False),
        'webhook': config.get('notifications.webhook', False),
        'webhook_url': config.get('notifications.webhook_url', ''),
        'quiet_hours_start': config.get('notifications.quiet_hours_start', ''),
        'quiet_hours_end': config.get('notifications.quiet_hours_end', ''),
        'min_change': config.get('notifications.min_change', 5),
        'min_volume': config.get('notifications.min_volume', 1000),
    }


def _save_notification_settings(config: Config, settings: dict):
    """Save notification settings"""
    config.set('notifications.desktop', settings.get('desktop', True))
    config.set('notifications.sound', settings.get('sound', False))
    config.set('notifications.webhook', settings.get('webhook', False))
    config.set('notifications.webhook_url', settings.get('webhook_url', ''))
    config.set('notifications.quiet_hours_start', settings.get('quiet_hours_start', ''))
    config.set('notifications.quiet_hours_end', settings.get('quiet_hours_end', ''))
    config.set('notifications.min_change', settings.get('min_change', 5))
    config.set('notifications.min_volume', settings.get('min_volume', 1000))


def _show_status(console: Console, settings: dict, output_format: str):
    """Show current notification status"""
    if output_format == 'json':
        print_json(settings)
        return

    console.print()
    console.print(Panel("[bold]Notification Settings[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Setting", width=20)
    table.add_column("Status", width=15)
    table.add_column("Details", width=30)

    # Desktop notifications
    desktop_status = "[green]Enabled[/green]" if settings['desktop'] else "[red]Disabled[/red]"
    table.add_row("Desktop Alerts", desktop_status, "System notification popups")

    # Sound
    sound_status = "[green]Enabled[/green]" if settings['sound'] else "[red]Disabled[/red]"
    table.add_row("Sound Alerts", sound_status, "Audible notification sounds")

    # Webhook
    webhook_status = "[green]Enabled[/green]" if settings['webhook'] else "[red]Disabled[/red]"
    webhook_url = settings['webhook_url'][:30] + "..." if len(settings['webhook_url']) > 30 else settings['webhook_url']
    table.add_row("Webhook", webhook_status, webhook_url or "[dim]Not configured[/dim]")

    console.print(table)
    console.print()

    # Thresholds
    console.print("[bold]Alert Thresholds:[/bold]")
    console.print()
    console.print(f"  Min Price Change: {settings['min_change']}%")
    console.print(f"  Min Volume: ${settings['min_volume']:,}")
    console.print()

    # Quiet hours
    if settings['quiet_hours_start'] and settings['quiet_hours_end']:
        console.print(f"[dim]Quiet Hours: {settings['quiet_hours_start']} - {settings['quiet_hours_end']}[/dim]")
    else:
        console.print("[dim]Quiet Hours: Not set[/dim]")

    console.print()


def _interactive_configure(console: Console, config: Config, settings: dict):
    """Interactive configuration"""
    console.print()
    console.print(Panel("[bold]Notification Configuration[/bold]", border_style="cyan"))
    console.print()

    # Desktop
    settings['desktop'] = Confirm.ask(
        "[cyan]Enable desktop notifications?[/cyan]",
        default=settings['desktop']
    )

    # Sound
    console.print()
    settings['sound'] = Confirm.ask(
        "[cyan]Enable sound alerts?[/cyan]",
        default=settings['sound']
    )

    # Webhook
    console.print()
    settings['webhook'] = Confirm.ask(
        "[cyan]Enable webhook notifications?[/cyan]",
        default=settings['webhook']
    )

    if settings['webhook']:
        console.print()
        console.print("[dim]Webhook URL (Discord, Slack, etc.)[/dim]")
        webhook_url = Prompt.ask("[cyan]Webhook URL[/cyan]", default=settings['webhook_url'])
        settings['webhook_url'] = webhook_url

    # Thresholds
    console.print()
    console.print("[cyan]Alert Thresholds:[/cyan]")

    min_change_str = Prompt.ask(
        "  Minimum price change (%)",
        default=str(settings['min_change'])
    )
    try:
        settings['min_change'] = float(min_change_str)
    except ValueError:
        pass

    min_volume_str = Prompt.ask(
        "  Minimum volume ($)",
        default=str(settings['min_volume'])
    )
    try:
        settings['min_volume'] = float(min_volume_str)
    except ValueError:
        pass

    # Quiet hours
    console.print()
    set_quiet = Confirm.ask("[cyan]Set quiet hours?[/cyan]", default=False)

    if set_quiet:
        settings['quiet_hours_start'] = Prompt.ask("  Start time (HH:MM)", default="22:00")
        settings['quiet_hours_end'] = Prompt.ask("  End time (HH:MM)", default="08:00")
    else:
        settings['quiet_hours_start'] = ''
        settings['quiet_hours_end'] = ''

    # Save
    _save_notification_settings(config, settings)

    console.print()
    console.print("[green]Notification settings saved![/green]")
    console.print()


def _test_notifications(console: Console, settings: dict):
    """Test notification channels"""
    console.print()
    console.print("[bold]Testing Notifications...[/bold]")
    console.print()

    # Test desktop
    if settings['desktop']:
        try:
            _send_desktop_notification(
                "PolyTerm Test",
                "Desktop notifications are working!"
            )
            console.print("[green]Desktop notification sent.[/green]")
        except Exception as e:
            console.print(f"[red]Desktop notification failed: {e}[/red]")
    else:
        console.print("[dim]Desktop notifications disabled.[/dim]")

    # Test sound
    if settings['sound']:
        try:
            _play_alert_sound()
            console.print("[green]Sound alert played.[/green]")
        except Exception as e:
            console.print(f"[red]Sound alert failed: {e}[/red]")
    else:
        console.print("[dim]Sound alerts disabled.[/dim]")

    # Test webhook
    if settings['webhook'] and settings['webhook_url']:
        try:
            _send_webhook_notification(
                settings['webhook_url'],
                "PolyTerm Test",
                "Webhook notifications are working!"
            )
            console.print("[green]Webhook notification sent.[/green]")
        except Exception as e:
            console.print(f"[red]Webhook notification failed: {e}[/red]")
    else:
        console.print("[dim]Webhook notifications disabled or not configured.[/dim]")

    console.print()


def _send_desktop_notification(title: str, message: str):
    """Send desktop notification"""
    import platform
    import subprocess

    system = platform.system()

    if system == "Darwin":  # macOS
        script = f'display notification "{message}" with title "{title}"'
        subprocess.run(["osascript", "-e", script], check=True)

    elif system == "Linux":
        subprocess.run(["notify-send", title, message], check=True)

    elif system == "Windows":
        # Use PowerShell for Windows notifications
        script = f'''
        [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
        $template = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
        $text = $template.GetElementsByTagName("text")
        $text[0].AppendChild($template.CreateTextNode("{title}")) | Out-Null
        $text[1].AppendChild($template.CreateTextNode("{message}")) | Out-Null
        $toast = [Windows.UI.Notifications.ToastNotification]::new($template)
        [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("PolyTerm").Show($toast)
        '''
        subprocess.run(["powershell", "-Command", script], check=True)


def _play_alert_sound():
    """Play alert sound"""
    import platform
    import subprocess

    system = platform.system()

    if system == "Darwin":  # macOS
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"], check=True)

    elif system == "Linux":
        # Try paplay (PulseAudio) or aplay (ALSA)
        try:
            subprocess.run(["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"], check=True)
        except Exception:
            subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], check=True)

    elif system == "Windows":
        import winsound
        winsound.MessageBeep()


def _send_webhook_notification(url: str, title: str, message: str):
    """Send webhook notification"""
    import json
    import urllib.request

    # Format for common webhook services
    if "discord" in url.lower():
        # Discord webhook format
        payload = {
            "embeds": [{
                "title": title,
                "description": message,
                "color": 5814783,  # Blue color
            }]
        }
    elif "slack" in url.lower():
        # Slack webhook format
        payload = {
            "text": f"*{title}*\n{message}"
        }
    else:
        # Generic webhook format
        payload = {
            "title": title,
            "message": message,
        }

    data = json.dumps(payload).encode('utf-8')

    req = urllib.request.Request(
        url,
        data=data,
        headers={'Content-Type': 'application/json'}
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status == 200 or response.status == 204
