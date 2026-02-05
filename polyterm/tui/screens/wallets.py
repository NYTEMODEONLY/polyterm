"""Wallets Screen - Smart money and whale wallet tracking"""

import subprocess
import sys
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table


def wallets_screen(console: RichConsole):
    """Track and analyze whale and smart money wallets

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Wallet Tracker[/bold]", style="cyan"))
    console.print()

    # Submenu for wallet operations
    console.print("[bold]Select Operation:[/bold]")
    console.print()

    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")

    menu.add_row("1", "View Whale Wallets - Highest volume traders")
    menu.add_row("2", "View Smart Money - High win rate wallets")
    menu.add_row("3", "View Suspicious - High risk score wallets")
    menu.add_row("4", "Analyze Wallet - Deep dive on specific wallet")
    menu.add_row("5", "Track Wallet - Add wallet to tracking list")
    menu.add_row("6", "Untrack Wallet - Remove from tracking list")
    menu.add_row("", "")
    menu.add_row("b", "Back - Return to main menu")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-6, b):[/cyan] ").strip().lower()
    console.print()

    if choice == '1':
        # Whale wallets
        limit = console.input(
            "How many wallets? [cyan][default: 20][/cyan] "
        ).strip() or "20"
        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        console.print("[green]Fetching whale wallets...[/green]")
        console.print()
        cmd = [sys.executable, "-m", "polyterm.cli.main", "wallets", "--type=whales", f"--limit={limit}"]

    elif choice == '2':
        # Smart money
        limit = console.input(
            "How many wallets? [cyan][default: 20][/cyan] "
        ).strip() or "20"
        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        console.print("[green]Fetching smart money wallets...[/green]")
        console.print()
        cmd = [sys.executable, "-m", "polyterm.cli.main", "wallets", "--type=smart", f"--limit={limit}"]

    elif choice == '3':
        # Suspicious
        limit = console.input(
            "How many wallets? [cyan][default: 20][/cyan] "
        ).strip() or "20"
        try:
            limit = int(limit)
        except ValueError:
            limit = 20

        console.print("[green]Fetching suspicious wallets...[/green]")
        console.print()
        cmd = [sys.executable, "-m", "polyterm.cli.main", "wallets", "--type=suspicious", f"--limit={limit}"]

    elif choice == '4':
        # Analyze specific wallet
        address = console.input(
            "[cyan]Enter wallet address:[/cyan] "
        ).strip()
        if not address:
            console.print("[red]No address provided[/red]")
            return

        console.print("[green]Analyzing wallet...[/green]")
        console.print()
        cmd = [sys.executable, "-m", "polyterm.cli.main", "wallets", f"--analyze={address}"]

    elif choice == '5':
        # Track wallet
        address = console.input(
            "[cyan]Enter wallet address to track:[/cyan] "
        ).strip()
        if not address:
            console.print("[red]No address provided[/red]")
            return

        cmd = [sys.executable, "-m", "polyterm.cli.main", "wallets", f"--track={address}"]

    elif choice == '6':
        # Untrack wallet
        address = console.input(
            "[cyan]Enter wallet address to untrack:[/cyan] "
        ).strip()
        if not address:
            console.print("[red]No address provided[/red]")
            return

        cmd = [sys.executable, "-m", "polyterm.cli.main", "wallets", f"--untrack={address}"]

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
