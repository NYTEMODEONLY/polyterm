"""My Wallet - Connect and view your Polymarket wallet activity"""

import click
from datetime import datetime, timezone
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...db.database import Database
from ...utils.json_output import print_json
from ...utils.config import Config


def is_valid_ethereum_address(address: str) -> bool:
    """Check if address is a valid Ethereum address"""
    if not address:
        return False
    # Basic validation: starts with 0x and is 42 characters
    if not address.startswith('0x'):
        return False
    if len(address) != 42:
        return False
    # Check hex characters
    try:
        int(address, 16)
        return True
    except ValueError:
        return False


def get_wallet_positions(subgraph_client: SubgraphClient, address: str) -> list:
    """Get wallet positions from subgraph"""
    try:
        positions = subgraph_client.get_user_positions(address)
        return positions if positions else []
    except Exception:
        return []


def get_wallet_trades(subgraph_client: SubgraphClient, address: str, limit: int = 50) -> list:
    """Get wallet trade history"""
    try:
        # Try to get trades where the wallet is involved
        trades = []
        # Subgraph client may have different methods
        return trades
    except Exception:
        return []


@click.command()
@click.option("--address", "-a", default=None, help="Wallet address to view")
@click.option("--connect", "-c", is_flag=True, help="Connect/save a wallet address")
@click.option("--disconnect", is_flag=True, help="Disconnect saved wallet")
@click.option("--positions", "-p", is_flag=True, help="View open positions")
@click.option("--history", "-h", "show_history", is_flag=True, help="View trade history")
@click.option("--pnl", is_flag=True, help="View P&L summary")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def mywallet(ctx, address, connect, disconnect, positions, show_history, pnl, interactive, output_format):
    """Connect your wallet and view your Polymarket activity

    This is a VIEW-ONLY feature - no private keys are stored or needed.
    You can track your positions, history, and P&L from your wallet address.

    Examples:
        polyterm mywallet -c                  # Connect a wallet
        polyterm mywallet -p                  # View positions
        polyterm mywallet -h                  # View trade history
        polyterm mywallet --pnl               # View P&L summary
        polyterm mywallet -i                  # Interactive mode
        polyterm mywallet -a 0x123...         # View specific wallet
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Get saved wallet address from config
    saved_address = config.get("wallet.address")

    # Use provided address or saved address
    wallet_address = address or saved_address

    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )

    subgraph_client = SubgraphClient(endpoint=config.subgraph_endpoint)

    try:
        # Connect new wallet
        if connect:
            console.print()
            console.print(Panel(
                "[bold cyan]Connect Your Wallet[/bold cyan]\n\n"
                "Enter your Polymarket wallet address to track your activity.\n"
                "[dim]This is VIEW-ONLY - no private keys required.[/dim]",
                border_style="cyan"
            ))
            console.print()

            new_address = Prompt.ask("[cyan]Wallet address (0x...)[/cyan]")

            if not is_valid_ethereum_address(new_address):
                console.print("[red]Invalid Ethereum address format[/red]")
                return

            # Save to config
            config.set("wallet.address", new_address)
            console.print(f"[green]Wallet connected:[/green] {new_address[:10]}...{new_address[-8:]}")
            console.print()
            console.print("[dim]Use 'polyterm mywallet -p' to view positions[/dim]")
            console.print("[dim]Use 'polyterm mywallet --pnl' to view P&L[/dim]")
            return

        # Disconnect wallet
        if disconnect:
            if saved_address:
                config.set("wallet.address", "")
                console.print(f"[yellow]Wallet disconnected:[/yellow] {saved_address[:10]}...{saved_address[-8:]}")
            else:
                console.print("[yellow]No wallet connected[/yellow]")
            return

        # Interactive mode
        if interactive:
            _interactive_mode(console, config, db, gamma_client, clob_client, subgraph_client)
            return

        # No wallet connected
        if not wallet_address:
            console.print()
            console.print("[yellow]No wallet connected[/yellow]")
            console.print()
            console.print("Connect a wallet to view your Polymarket activity:")
            console.print("  [cyan]polyterm mywallet --connect[/cyan]")
            console.print()
            console.print("Or view any wallet with:")
            console.print("  [cyan]polyterm mywallet -a 0x...[/cyan]")
            return

        # Validate address
        if not is_valid_ethereum_address(wallet_address):
            console.print("[red]Invalid wallet address format[/red]")
            return

        # Show wallet info header
        short_address = f"{wallet_address[:10]}...{wallet_address[-8:]}"

        if output_format != 'json':
            console.print()
            is_saved = wallet_address == saved_address
            status = "[green](Connected)[/green]" if is_saved else "[dim](Viewing)[/dim]"
            console.print(f"[bold]Wallet:[/bold] {short_address} {status}")
            console.print()

        # View positions
        if positions:
            _show_positions(console, wallet_address, subgraph_client, db, output_format)
            return

        # View history
        if show_history:
            _show_history(console, wallet_address, subgraph_client, db, output_format)
            return

        # View P&L
        if pnl:
            _show_pnl(console, wallet_address, subgraph_client, db, output_format)
            return

        # Default: show summary
        _show_summary(console, wallet_address, subgraph_client, db, output_format)

    finally:
        gamma_client.close()
        clob_client.close()


def _interactive_mode(console, config, db, gamma_client, clob_client, subgraph_client):
    """Interactive wallet management mode"""
    console.print()
    console.print(Panel(
        "[bold cyan]My Wallet[/bold cyan]\n\n"
        "View and track your Polymarket activity.\n"
        "[dim]VIEW-ONLY - no private keys required[/dim]",
        border_style="cyan"
    ))
    console.print()

    saved_address = config.get("wallet.address")

    if saved_address:
        short = f"{saved_address[:10]}...{saved_address[-8:]}"
        console.print(f"[green]Connected wallet:[/green] {short}")
    else:
        console.print("[yellow]No wallet connected[/yellow]")

    console.print()
    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Connect/change wallet")
    console.print("  [cyan]2[/cyan] - View positions")
    console.print("  [cyan]3[/cyan] - View trade history")
    console.print("  [cyan]4[/cyan] - View P&L summary")
    console.print("  [cyan]5[/cyan] - Disconnect wallet")
    console.print("  [cyan]q[/cyan] - Quit")
    console.print()

    while True:
        choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "4", "5", "q"], default="q")

        if choice == "q":
            break

        elif choice == "1":
            # Connect wallet
            new_address = Prompt.ask("[cyan]Wallet address (0x...)[/cyan]")
            if is_valid_ethereum_address(new_address):
                config.set("wallet.address", new_address)
                saved_address = new_address
                console.print(f"[green]Wallet connected:[/green] {new_address[:10]}...{new_address[-8:]}")
            else:
                console.print("[red]Invalid address format[/red]")

        elif choice == "2":
            if saved_address:
                _show_positions(console, saved_address, subgraph_client, db, "table")
            else:
                console.print("[yellow]Connect a wallet first[/yellow]")

        elif choice == "3":
            if saved_address:
                _show_history(console, saved_address, subgraph_client, db, "table")
            else:
                console.print("[yellow]Connect a wallet first[/yellow]")

        elif choice == "4":
            if saved_address:
                _show_pnl(console, saved_address, subgraph_client, db, "table")
            else:
                console.print("[yellow]Connect a wallet first[/yellow]")

        elif choice == "5":
            if saved_address:
                config.set("wallet.address", "")
                console.print(f"[yellow]Wallet disconnected[/yellow]")
                saved_address = None
            else:
                console.print("[yellow]No wallet connected[/yellow]")

        console.print()


def _show_positions(console, address, subgraph_client, db, output_format):
    """Show wallet positions"""
    console.print("[bold]Open Positions[/bold]")
    console.print()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task("Fetching positions...", total=None)

        positions = get_wallet_positions(subgraph_client, address)

        # Also check locally tracked positions
        local_positions = db.get_positions(status='open')

    if output_format == 'json':
        print_json({
            'success': True,
            'wallet': address,
            'positions': positions,
            'local_positions': local_positions,
        })
        return

    if not positions and not local_positions:
        console.print("[dim]No open positions found[/dim]")
        console.print()
        console.print("[dim]Note: On-chain position data may be limited.[/dim]")
        console.print("[dim]Use 'polyterm position --add' to manually track positions.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Market", max_width=35)
    table.add_column("Side", width=8)
    table.add_column("Shares", justify="right", width=10)
    table.add_column("Entry", justify="right", width=10)
    table.add_column("Value", justify="right", width=12)
    table.add_column("Source", width=10)

    # Show on-chain positions
    for pos in positions:
        market_title = pos.get('market', {}).get('question', 'Unknown')[:35]
        side = pos.get('outcome', 'YES')
        shares = float(pos.get('shares', 0))
        entry = float(pos.get('avgPrice', 0))
        value = shares * entry

        table.add_row(
            market_title,
            f"[green]{side}[/green]" if side == "YES" else f"[red]{side}[/red]",
            f"{shares:,.1f}",
            f"${entry:.3f}",
            f"${value:,.2f}",
            "[cyan]Chain[/cyan]",
        )

    # Show locally tracked positions
    for pos in local_positions:
        table.add_row(
            pos['title'][:35],
            f"[green]{pos['side'].upper()}[/green]" if pos['side'].lower() == "yes" else f"[red]{pos['side'].upper()}[/red]",
            f"{pos['shares']:,.1f}",
            f"${pos['entry_price']:.3f}",
            f"${pos['shares'] * pos['entry_price']:,.2f}",
            "[dim]Local[/dim]",
        )

    console.print(table)
    console.print()


def _show_history(console, address, subgraph_client, db, output_format):
    """Show wallet trade history"""
    console.print("[bold]Recent Trade History[/bold]")
    console.print()

    # Get trades from database (we track followed wallet activity)
    trades = db.get_trades_by_wallet(address, limit=20)

    if output_format == 'json':
        print_json({
            'success': True,
            'wallet': address,
            'trades': [t.to_dict() for t in trades],
        })
        return

    if not trades:
        console.print("[dim]No trade history found[/dim]")
        console.print()
        console.print("[dim]Trade history is captured when monitoring markets.[/dim]")
        console.print("[dim]Run 'polyterm whales' or 'polyterm live-monitor' to capture trades.[/dim]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Date", width=12)
    table.add_column("Market", max_width=30)
    table.add_column("Side", width=8)
    table.add_column("Price", justify="right", width=8)
    table.add_column("Size", justify="right", width=10)
    table.add_column("Notional", justify="right", width=12)

    for trade in trades:
        date_str = trade.timestamp.strftime("%m/%d %H:%M")
        market = trade.market_slug or trade.market_id[:20]
        side_color = "green" if trade.side.lower() in ["buy", "yes"] else "red"

        table.add_row(
            date_str,
            market[:30],
            f"[{side_color}]{trade.side.upper()}[/{side_color}]",
            f"${trade.price:.3f}",
            f"{trade.size:,.1f}",
            f"${trade.notional:,.2f}",
        )

    console.print(table)
    console.print()


def _show_pnl(console, address, subgraph_client, db, output_format):
    """Show P&L summary"""
    console.print("[bold]P&L Summary[/bold]")
    console.print()

    # Get position summary from local tracking
    summary = db.get_position_summary()

    # Get wallet stats if available
    wallet = db.get_wallet(address)

    if output_format == 'json':
        print_json({
            'success': True,
            'wallet': address,
            'position_summary': summary,
            'wallet_stats': wallet.to_dict() if wallet else None,
        })
        return

    table = Table(show_header=False, box=None)
    table.add_column(width=25)
    table.add_column(width=15, justify="right")

    table.add_row("[bold]Position Tracking:[/bold]", "")
    table.add_row("  Open Positions", f"{summary['open_positions']}")
    table.add_row("  Open Value", f"${summary['open_value']:,.2f}")
    table.add_row("  Closed Trades", f"{summary['closed_positions']}")
    table.add_row("", "")

    # P&L
    realized = summary['realized_pnl']
    pnl_color = "green" if realized >= 0 else "red"
    table.add_row("[bold]Performance:[/bold]", "")
    table.add_row("  Realized P&L", f"[{pnl_color}]${realized:+,.2f}[/{pnl_color}]")
    table.add_row("  Wins", f"[green]{summary['wins']}[/green]")
    table.add_row("  Losses", f"[red]{summary['losses']}[/red]")
    table.add_row("  Win Rate", f"{summary['win_rate']:.1f}%")

    if wallet:
        table.add_row("", "")
        table.add_row("[bold]Wallet Stats:[/bold]", "")
        table.add_row("  Total Trades", f"{wallet.total_trades}")
        table.add_row("  Total Volume", f"${wallet.total_volume:,.2f}")
        table.add_row("  Avg Position", f"${wallet.avg_position_size:,.2f}")

    console.print(table)
    console.print()

    if summary['open_positions'] == 0 and summary['closed_positions'] == 0:
        console.print("[dim]No tracked positions yet.[/dim]")
        console.print("[dim]Use 'polyterm position --add' to manually track trades.[/dim]")
        console.print()


def _show_summary(console, address, subgraph_client, db, output_format):
    """Show wallet summary"""

    # Get all data
    positions = get_wallet_positions(subgraph_client, address)
    local_positions = db.get_positions(status='open')
    wallet = db.get_wallet(address)
    summary = db.get_position_summary()

    if output_format == 'json':
        print_json({
            'success': True,
            'wallet': address,
            'positions_count': len(positions) + len(local_positions),
            'position_summary': summary,
            'wallet_stats': wallet.to_dict() if wallet else None,
        })
        return

    # Summary panel
    total_positions = len(positions) + len(local_positions)

    console.print("[bold]Wallet Summary[/bold]")
    console.print()

    table = Table(show_header=False, box=None)
    table.add_column(width=25)
    table.add_column(width=15, justify="right")

    table.add_row("Open Positions", f"{total_positions}")
    table.add_row("Tracked Value", f"${summary['open_value']:,.2f}")

    if wallet:
        table.add_row("Total Trades (tracked)", f"{wallet.total_trades}")
        table.add_row("Total Volume (tracked)", f"${wallet.total_volume:,.2f}")

    realized = summary['realized_pnl']
    if summary['closed_positions'] > 0:
        pnl_color = "green" if realized >= 0 else "red"
        table.add_row("Realized P&L", f"[{pnl_color}]${realized:+,.2f}[/{pnl_color}]")

    console.print(table)
    console.print()

    console.print("[bold]Quick Actions:[/bold]")
    console.print("  [cyan]polyterm mywallet -p[/cyan]     View positions")
    console.print("  [cyan]polyterm mywallet -h[/cyan]     View history")
    console.print("  [cyan]polyterm mywallet --pnl[/cyan]  View P&L details")
    console.print("  [cyan]polyterm position --add[/cyan]  Track a position")
    console.print()
