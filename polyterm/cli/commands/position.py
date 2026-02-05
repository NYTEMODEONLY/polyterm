"""Position Tracker - Track trades and P&L without wallet connection"""

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
@click.option("--list", "-l", "list_positions", is_flag=True, help="List all positions")
@click.option("--open", "show_open", is_flag=True, help="Show only open positions")
@click.option("--closed", "show_closed", is_flag=True, help="Show only closed positions")
@click.option("--add", "-a", "add_market", default=None, help="Add position for market")
@click.option("--close", "-c", "close_id", type=int, default=None, help="Close position by ID")
@click.option("--delete", "-d", "delete_id", type=int, default=None, help="Delete position by ID")
@click.option("--summary", "-s", is_flag=True, help="Show P&L summary")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def position(ctx, list_positions, show_open, show_closed, add_market, close_id, delete_id, summary, interactive, output_format):
    """Track positions and P&L manually

    Track your trades without connecting a wallet. Useful for:
    - Paper trading and tracking hypothetical positions
    - Privacy (no wallet connection needed)
    - Tracking positions across multiple platforms

    Examples:
        polyterm position --list                # List all positions
        polyterm position --add "bitcoin"       # Add new position
        polyterm position --close 1             # Close position #1
        polyterm position --summary             # View P&L summary
        polyterm position -i                    # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Delete position
    if delete_id:
        if db.delete_position(delete_id):
            if output_format == 'json':
                print_json({'success': True, 'action': 'deleted', 'position_id': delete_id})
            else:
                console.print(f"[green]Position #{delete_id} deleted.[/green]")
        else:
            if output_format == 'json':
                print_json({'success': False, 'error': f'Position #{delete_id} not found'})
            else:
                console.print(f"[yellow]Position #{delete_id} not found.[/yellow]")
        return

    # Close position
    if close_id:
        _close_position(console, config, db, close_id, output_format)
        return

    # Add position
    if add_market:
        _add_position(console, config, db, add_market, output_format)
        return

    # Show summary
    if summary:
        _show_summary(console, db, output_format)
        return

    # Interactive mode
    if interactive:
        _interactive_mode(console, config, db)
        return

    # List positions (default)
    status = None
    if show_open:
        status = 'open'
    elif show_closed:
        status = 'closed'

    _list_positions(console, config, db, status, output_format)


def _list_positions(console: Console, config, db: Database, status: str, output_format: str):
    """List tracked positions"""
    positions = db.get_positions(status=status)

    if output_format == 'json':
        print_json({
            'success': True,
            'status_filter': status,
            'count': len(positions),
            'positions': positions,
        })
        return

    if not positions:
        console.print("[yellow]No positions tracked.[/yellow]")
        console.print("[dim]Use 'polyterm position -i' to add positions.[/dim]")
        return

    console.print()

    title = "Positions"
    if status == 'open':
        title = "Open Positions"
    elif status == 'closed':
        title = "Closed Positions"

    console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
    console.print()

    # Get current prices for open positions
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", style="dim", width=4)
    table.add_column("Market", max_width=35)
    table.add_column("Side", width=5)
    table.add_column("Shares", justify="right", width=8)
    table.add_column("Entry", justify="right", width=7)
    table.add_column("Current", justify="right", width=7)
    table.add_column("P&L", justify="right", width=10)
    table.add_column("Status", width=8)

    total_pnl = 0

    try:
        for pos in positions:
            entry_price = pos['entry_price']
            shares = pos['shares']
            side = pos['side'].upper()

            # Get current price for open positions
            if pos['status'] == 'open':
                try:
                    market = gamma_client.get_market(pos['market_id'])
                    if market:
                        import json
                        outcome_prices = market.get('outcomePrices', [])
                        if isinstance(outcome_prices, str):
                            outcome_prices = json.loads(outcome_prices)
                        current_price = float(outcome_prices[0]) if outcome_prices else entry_price
                    else:
                        current_price = entry_price
                except Exception:
                    current_price = entry_price
            else:
                current_price = pos['exit_price'] if pos['exit_price'] else entry_price

            # Calculate P&L based on side
            if side == 'YES':
                # Bought YES: profit if price goes up
                pnl = (current_price - entry_price) * shares
            else:
                # Bought NO: profit if price goes down
                pnl = (entry_price - current_price) * shares

            total_pnl += pnl

            # Format
            pnl_color = "green" if pnl >= 0 else "red"
            side_color = "green" if side == "YES" else "red"
            status_color = "cyan" if pos['status'] == 'open' else "dim"

            table.add_row(
                str(pos['id']),
                pos['title'][:33],
                f"[{side_color}]{side}[/{side_color}]",
                f"{shares:.1f}",
                f"{entry_price * 100:.0f}%",
                f"{current_price * 100:.0f}%",
                f"[{pnl_color}]${pnl:+,.2f}[/{pnl_color}]",
                f"[{status_color}]{pos['status']}[/{status_color}]",
            )

        console.print(table)
        console.print()

        # Summary line
        pnl_color = "green" if total_pnl >= 0 else "red"
        console.print(f"[bold]Total P&L: [{pnl_color}]${total_pnl:+,.2f}[/{pnl_color}][/bold]")
        console.print()

    finally:
        gamma_client.close()


def _add_position(console: Console, config, db: Database, search_term: str, output_format: str):
    """Add a new position"""
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
            except (json.JSONDecodeError, ValueError):
                outcome_prices = []
        current_price = float(outcome_prices[0]) if outcome_prices else 0.5

        console.print()
        console.print(f"[bold]{title}[/bold]")
        console.print(f"Current price: [cyan]{current_price * 100:.1f}%[/cyan]")
        console.print()

        # Get position details
        side = Prompt.ask(
            "[cyan]Side (YES or NO)[/cyan]",
            choices=["yes", "no", "YES", "NO"],
            default="YES"
        ).upper()

        shares = FloatPrompt.ask("[cyan]Number of shares[/cyan]", default=100.0)

        entry_input = FloatPrompt.ask(
            "[cyan]Entry price (e.g., 65 for 65%)[/cyan]",
            default=current_price * 100
        )
        entry_price = entry_input / 100 if entry_input > 1 else entry_input

        platform = Prompt.ask(
            "[cyan]Platform[/cyan]",
            choices=["polymarket", "kalshi", "other"],
            default="polymarket"
        )

        notes = Prompt.ask("[cyan]Notes (optional)[/cyan]", default="")

        # Calculate position value
        position_value = shares * entry_price

        console.print()
        console.print(f"[bold]Position Summary:[/bold]")
        console.print(f"  {side} @ {entry_price * 100:.1f}%")
        console.print(f"  {shares:.1f} shares = ${position_value:,.2f}")

        if Confirm.ask("[cyan]Add this position?[/cyan]", default=True):
            position_id = db.add_position(
                market_id=market_id,
                title=title,
                side=side,
                shares=shares,
                entry_price=entry_price,
                platform=platform,
                notes=notes,
            )

            if output_format == 'json':
                print_json({
                    'success': True,
                    'action': 'added',
                    'position_id': position_id,
                    'market_id': market_id,
                    'side': side,
                    'shares': shares,
                    'entry_price': entry_price,
                })
            else:
                console.print()
                console.print(f"[green]Position #{position_id} added![/green]")
        else:
            console.print("[yellow]Cancelled.[/yellow]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _close_position(console: Console, config, db: Database, position_id: int, output_format: str):
    """Close a position"""
    position = db.get_position(position_id)

    if not position:
        if output_format == 'json':
            print_json({'success': False, 'error': f'Position #{position_id} not found'})
        else:
            console.print(f"[yellow]Position #{position_id} not found.[/yellow]")
        return

    if position['status'] != 'open':
        if output_format == 'json':
            print_json({'success': False, 'error': f'Position #{position_id} is already closed'})
        else:
            console.print(f"[yellow]Position #{position_id} is already closed.[/yellow]")
        return

    console.print()
    console.print(f"[bold]Closing Position #{position_id}[/bold]")
    console.print(f"  {position['title'][:50]}")
    console.print(f"  {position['side']} @ {position['entry_price'] * 100:.1f}%")
    console.print()

    # Get current price
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        market = gamma_client.get_market(position['market_id'])
        if market:
            import json
            outcome_prices = market.get('outcomePrices', [])
            if isinstance(outcome_prices, str):
                outcome_prices = json.loads(outcome_prices)
            current_price = float(outcome_prices[0]) if outcome_prices else position['entry_price']
        else:
            current_price = position['entry_price']

        console.print(f"Current market price: [cyan]{current_price * 100:.1f}%[/cyan]")

    except Exception:
        current_price = position['entry_price']
    finally:
        gamma_client.close()

    # Get exit price
    exit_input = FloatPrompt.ask(
        "[cyan]Exit price (e.g., 75 for 75%)[/cyan]",
        default=current_price * 100
    )
    exit_price = exit_input / 100 if exit_input > 1 else exit_input

    # Calculate P&L
    if position['side'] == 'YES':
        pnl = (exit_price - position['entry_price']) * position['shares']
    else:
        pnl = (position['entry_price'] - exit_price) * position['shares']

    pnl_color = "green" if pnl >= 0 else "red"
    console.print(f"P&L: [{pnl_color}]${pnl:+,.2f}[/{pnl_color}]")

    # Determine status
    status = Prompt.ask(
        "[cyan]Status[/cyan]",
        choices=["closed", "won", "lost"],
        default="won" if pnl > 0 else "lost" if pnl < 0 else "closed"
    )

    if Confirm.ask("[cyan]Close this position?[/cyan]", default=True):
        db.close_position(position_id, exit_price, status)

        if output_format == 'json':
            print_json({
                'success': True,
                'action': 'closed',
                'position_id': position_id,
                'exit_price': exit_price,
                'pnl': pnl,
            })
        else:
            console.print()
            console.print(f"[green]Position #{position_id} closed![/green]")
    else:
        console.print("[yellow]Cancelled.[/yellow]")


def _show_summary(console: Console, db: Database, output_format: str):
    """Show P&L summary"""
    summary = db.get_position_summary()

    if output_format == 'json':
        print_json({
            'success': True,
            **summary,
        })
        return

    console.print()
    console.print(Panel("[bold]Position Summary[/bold]", border_style="cyan"))
    console.print()

    # Open positions
    console.print("[bold yellow]Open Positions[/bold yellow]")
    console.print(f"  Count: [cyan]{summary['open_positions']}[/cyan]")
    console.print(f"  Value: [cyan]${summary['open_value']:,.2f}[/cyan]")
    console.print()

    # Closed positions
    console.print("[bold yellow]Closed Positions[/bold yellow]")
    console.print(f"  Count: [cyan]{summary['closed_positions']}[/cyan]")

    pnl = summary['realized_pnl']
    pnl_color = "green" if pnl >= 0 else "red"
    console.print(f"  Realized P&L: [{pnl_color}]${pnl:+,.2f}[/{pnl_color}]")
    console.print()

    # Win/Loss
    console.print("[bold yellow]Performance[/bold yellow]")
    console.print(f"  Wins: [green]{summary['wins']}[/green]")
    console.print(f"  Losses: [red]{summary['losses']}[/red]")

    wr = summary['win_rate']
    wr_color = "green" if wr >= 50 else "yellow" if wr >= 40 else "red"
    console.print(f"  Win Rate: [{wr_color}]{wr:.1f}%[/{wr_color}]")
    console.print()


def _interactive_mode(console: Console, config, db: Database):
    """Interactive position management"""
    console.print(Panel(
        "[bold]Position Tracker[/bold]\n\n"
        "[dim]Track your trades and P&L without connecting a wallet.[/dim]",
        title="[cyan]Positions[/cyan]",
        border_style="cyan",
    ))
    console.print()

    while True:
        console.print("[bold]Options:[/bold]")
        console.print("  [cyan]1.[/cyan] View open positions")
        console.print("  [cyan]2.[/cyan] View all positions")
        console.print("  [cyan]3.[/cyan] Add new position")
        console.print("  [cyan]4.[/cyan] Close a position")
        console.print("  [cyan]5.[/cyan] View P&L summary")
        console.print("  [cyan]q.[/cyan] Exit")
        console.print()

        choice = Prompt.ask("[cyan]Select option[/cyan]", default="q")

        if choice == '1':
            _list_positions(console, config, db, 'open', "table")
        elif choice == '2':
            _list_positions(console, config, db, None, "table")
        elif choice == '3':
            search = Prompt.ask("[cyan]Search for market[/cyan]")
            if search:
                _add_position(console, config, db, search, "table")
        elif choice == '4':
            positions = db.get_positions(status='open')
            if positions:
                _list_positions(console, config, db, 'open', "table")
                pos_id = Prompt.ask("[cyan]Enter position ID to close[/cyan]", default="")
                if pos_id:
                    try:
                        _close_position(console, config, db, int(pos_id), "table")
                    except ValueError:
                        console.print("[red]Invalid ID.[/red]")
            else:
                console.print("[yellow]No open positions to close.[/yellow]")
        elif choice == '5':
            _show_summary(console, db, "table")
        elif choice.lower() == 'q':
            break

        console.print()
