"""Alerts Screen - View and manage alerts"""

import subprocess
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table


def alerts_screen(console: RichConsole):
    """View and manage alerts

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Alert Center[/bold]", style="cyan"))
    console.print()

    # Submenu for alert operations
    console.print("[bold]Select Operation:[/bold]")
    console.print()

    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")

    menu.add_row("1", "View All Alerts - Recent alerts of all types")
    menu.add_row("2", "View Unread - Only unacknowledged alerts")
    menu.add_row("3", "Filter by Type - Whale, insider, arbitrage, etc.")
    menu.add_row("4", "Acknowledge Alert - Mark alert as read")
    menu.add_row("5", "Test Telegram - Send test notification")
    menu.add_row("6", "Test Discord - Send test notification")
    menu.add_row("", "")
    menu.add_row("b", "Back - Return to main menu")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-6, b):[/cyan] ").strip().lower()
    console.print()

    if choice == '1':
        # All alerts
        limit = console.input(
            "How many alerts? [cyan][default: 20][/cyan] "
        ).strip() or "20"
        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        console.print("[green]Fetching alerts...[/green]")
        console.print()
        cmd = ["polyterm", "alerts", f"--limit={limit}"]

    elif choice == '2':
        # Unread only
        limit = console.input(
            "How many alerts? [cyan][default: 20][/cyan] "
        ).strip() or "20"
        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        console.print("[green]Fetching unread alerts...[/green]")
        console.print()
        cmd = ["polyterm", "alerts", "--unread", f"--limit={limit}"]

    elif choice == '3':
        # Filter by type
        console.print("Alert types: whale, insider, arbitrage, smart_money")
        alert_type = console.input(
            "[cyan]Enter alert type:[/cyan] "
        ).strip().lower()

        valid_types = ['whale', 'insider', 'arbitrage', 'smart_money']
        if alert_type not in valid_types:
            console.print(f"[red]Invalid type. Choose from: {', '.join(valid_types)}[/red]")
            return

        limit = console.input(
            "How many alerts? [cyan][default: 20][/cyan] "
        ).strip() or "20"
        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        console.print(f"[green]Fetching {alert_type} alerts...[/green]")
        console.print()
        cmd = ["polyterm", "alerts", f"--type={alert_type}", f"--limit={limit}"]

    elif choice == '4':
        # Acknowledge alert
        alert_id = console.input(
            "[cyan]Enter alert ID to acknowledge:[/cyan] "
        ).strip()
        if not alert_id:
            console.print("[red]No ID provided[/red]")
            return
        try:
            alert_id = int(alert_id)
        except ValueError:
            console.print("[red]Invalid alert ID[/red]")
            return

        cmd = ["polyterm", "alerts", f"--ack={alert_id}"]

    elif choice == '5':
        # Test Telegram
        console.print("[green]Sending Telegram test notification...[/green]")
        console.print()
        cmd = ["polyterm", "alerts", "--test-telegram"]

    elif choice == '6':
        # Test Discord
        console.print("[green]Sending Discord test notification...[/green]")
        console.print()
        cmd = ["polyterm", "alerts", "--test-discord"]

    elif choice == 'b':
        return

    else:
        console.print("[red]Invalid option[/red]")
        return

    try:
        result = subprocess.run(cmd, capture_output=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
