"""Follow command - Copy trading and wallet following"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--add", "-a", default=None, help="Follow a wallet address")
@click.option("--remove", "-r", default=None, help="Unfollow a wallet address")
@click.option("--list", "list_followed", is_flag=True, help="List followed wallets")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
def follow(add, remove, list_followed, output_format):
    """Manage followed wallets for copy trading

    Follow successful traders to see their moves and learn from their strategies.

    Examples:
        polyterm follow --list                    # List followed wallets
        polyterm follow --add 0x1234...           # Follow a wallet
        polyterm follow --remove 0x1234...        # Unfollow a wallet
    """
    console = Console()
    db = Database()

    # If no options, show interactive menu
    if not add and not remove and not list_followed:
        _interactive_mode(console, db)
        return

    # List followed wallets
    if list_followed:
        followed = db.get_followed_wallets()

        if output_format == 'json':
            print_json({
                'success': True,
                'count': len(followed),
                'wallets': [w.to_dict() for w in followed],
            })
            return

        if not followed:
            console.print("[yellow]You're not following any wallets yet.[/yellow]")
            console.print("[dim]Use 'polyterm follow --add <address>' to start following.[/dim]")
            return

        _display_followed(console, followed)
        return

    # Add a wallet
    if add:
        address = add.strip()
        if db.is_following(address):
            if output_format == 'json':
                print_json({'success': False, 'error': 'Already following this wallet'})
            else:
                console.print(f"[yellow]You're already following {address[:10]}...[/yellow]")
            return

        # Check followed count (limit to 10)
        followed_count = len(db.get_followed_wallets())
        if followed_count >= 10:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Maximum 10 followed wallets'})
            else:
                console.print("[red]You can follow a maximum of 10 wallets.[/red]")
                console.print("[dim]Unfollow some wallets first with 'polyterm follow --remove <address>'[/dim]")
            return

        db.follow_wallet(address)

        if output_format == 'json':
            print_json({'success': True, 'action': 'followed', 'address': address})
        else:
            console.print(f"[green]Now following {address}[/green]")
            console.print("[dim]You'll see this wallet's activity in alerts.[/dim]")
        return

    # Remove a wallet
    if remove:
        address = remove.strip()
        if not db.is_following(address):
            if output_format == 'json':
                print_json({'success': False, 'error': 'Not following this wallet'})
            else:
                console.print(f"[yellow]You're not following {address[:10]}...[/yellow]")
            return

        db.unfollow_wallet(address)

        if output_format == 'json':
            print_json({'success': True, 'action': 'unfollowed', 'address': address})
        else:
            console.print(f"[green]Unfollowed {address}[/green]")


def _interactive_mode(console: Console, db: Database):
    """Interactive wallet following management"""
    console.print(Panel(
        "[bold]Copy Trading - Wallet Following[/bold]\n"
        "[dim]Follow successful traders to learn from their moves[/dim]",
        style="cyan"
    ))
    console.print()

    while True:
        followed = db.get_followed_wallets()

        console.print(f"[cyan]Following {len(followed)}/10 wallets[/cyan]")
        console.print()
        console.print("  [bold]1.[/bold] List followed wallets")
        console.print("  [bold]2.[/bold] Follow a new wallet")
        console.print("  [bold]3.[/bold] Unfollow a wallet")
        console.print("  [bold]q.[/bold] Return to menu")
        console.print()

        choice = Prompt.ask("[cyan]Select option[/cyan]", choices=["1", "2", "3", "q"], default="1")

        if choice == "q":
            break

        if choice == "1":
            console.print()
            if not followed:
                console.print("[yellow]You're not following any wallets yet.[/yellow]")
            else:
                _display_followed(console, followed)

        elif choice == "2":
            console.print()
            if len(followed) >= 10:
                console.print("[red]You can follow a maximum of 10 wallets.[/red]")
                console.print("[dim]Unfollow some wallets first.[/dim]")
            else:
                console.print("[bold]Where to find wallet addresses:[/bold]")
                console.print("  - Run 'polyterm wallets --type smart' to find smart money")
                console.print("  - Run 'polyterm wallets --type whales' to find whales")
                console.print("  - Copy addresses from Polymarket activity")
                console.print()
                address = Prompt.ask("[cyan]Enter wallet address to follow[/cyan]")
                if address and len(address) > 10:
                    if db.is_following(address):
                        console.print("[yellow]Already following this wallet.[/yellow]")
                    else:
                        db.follow_wallet(address)
                        console.print(f"[green]Now following {address}[/green]")
                else:
                    console.print("[yellow]Invalid address.[/yellow]")

        elif choice == "3":
            console.print()
            if not followed:
                console.print("[yellow]You're not following any wallets.[/yellow]")
            else:
                console.print("[bold]Select wallet to unfollow:[/bold]")
                for i, w in enumerate(followed, 1):
                    addr_short = f"{w.address[:6]}...{w.address[-4:]}"
                    console.print(f"  [cyan]{i}.[/cyan] {addr_short} (Win: {w.win_rate*100:.0f}%)")

                console.print()
                choice_num = Prompt.ask(
                    "[cyan]Enter number[/cyan]",
                    choices=[str(i) for i in range(1, len(followed) + 1)] + ["q"],
                    default="q"
                )
                if choice_num != "q":
                    wallet = followed[int(choice_num) - 1]
                    if Confirm.ask(f"[yellow]Unfollow {wallet.address[:10]}...?[/yellow]"):
                        db.unfollow_wallet(wallet.address)
                        console.print("[green]Unfollowed.[/green]")

        console.print()


def _display_followed(console: Console, wallets):
    """Display followed wallets in a table"""
    table = Table(title="Followed Wallets", show_header=True)
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Address", style="cyan")
    table.add_column("Win Rate", justify="right")
    table.add_column("Volume", justify="right")
    table.add_column("Trades", justify="right")
    table.add_column("Avg Size", justify="right")

    for i, w in enumerate(wallets, 1):
        addr_short = f"{w.address[:6]}...{w.address[-4:]}"

        # Color code win rate
        win_rate = w.win_rate * 100
        if win_rate >= 70:
            win_style = "green"
        elif win_rate >= 50:
            win_style = "yellow"
        else:
            win_style = "red"

        table.add_row(
            str(i),
            addr_short,
            f"[{win_style}]{win_rate:.0f}%[/{win_style}]",
            f"${w.total_volume:,.0f}",
            str(w.total_trades),
            f"${w.avg_position_size:,.0f}" if w.avg_position_size > 0 else "-",
        )

    console.print(table)
    console.print()
    console.print("[dim]Tip: Set up alerts to get notified when followed wallets trade.[/dim]")
