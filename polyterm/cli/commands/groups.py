"""Watchlist Groups - Organize markets into named collections"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--list", "-l", "list_groups", is_flag=True, help="List all groups")
@click.option("--create", "-c", "create_name", default=None, help="Create new group")
@click.option("--view", "-v", "view_group", default=None, help="View group markets")
@click.option("--add", "-a", "add_to", default=None, help="Add market to group")
@click.option("--remove", "-r", "remove_from", default=None, help="Remove market from group")
@click.option("--delete", "-d", "delete_group", default=None, help="Delete a group")
@click.option("--market", "-m", default=None, help="Market to add/remove")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def groups(ctx, list_groups, create_name, view_group, add_to, remove_from, delete_group, market, output_format):
    """Organize markets into named watchlist groups

    Create collections of related markets for easy tracking.

    Examples:
        polyterm groups --list                           # List all groups
        polyterm groups --create "crypto"                # Create new group
        polyterm groups --view "crypto"                  # View group markets
        polyterm groups --add "crypto" -m "bitcoin"      # Add market to group
        polyterm groups --remove "crypto" -m "bitcoin"   # Remove from group
        polyterm groups --delete "crypto"                # Delete group
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Initialize groups table
    _init_groups_table(db)

    # Delete group
    if delete_group:
        _delete_group(console, db, delete_group, output_format)
        return

    # Create group
    if create_name:
        _create_group(console, db, create_name, output_format)
        return

    # View group
    if view_group:
        _view_group(console, config, db, view_group, output_format)
        return

    # Add to group
    if add_to and market:
        _add_to_group(console, config, db, add_to, market, output_format)
        return

    # Remove from group
    if remove_from and market:
        _remove_from_group(console, db, remove_from, market, output_format)
        return

    # Default: list groups
    _list_groups(console, db, output_format)


def _init_groups_table(db: Database):
    """Initialize groups tables"""
    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Groups table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                created_at TIMESTAMP NOT NULL
            )
        """)

        # Group members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS group_members (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                market_id TEXT NOT NULL,
                title TEXT NOT NULL,
                added_at TIMESTAMP NOT NULL,
                FOREIGN KEY (group_id) REFERENCES watchlist_groups(id),
                UNIQUE(group_id, market_id)
            )
        """)


def _list_groups(console: Console, db: Database, output_format: str):
    """List all groups"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.*, COUNT(m.id) as member_count
            FROM watchlist_groups g
            LEFT JOIN group_members m ON g.id = m.group_id
            GROUP BY g.id
            ORDER BY g.name
        """)
        groups_list = [dict(row) for row in cursor.fetchall()]

    if output_format == 'json':
        print_json({'success': True, 'count': len(groups_list), 'groups': groups_list})
        return

    console.print()
    console.print(Panel("[bold]Watchlist Groups[/bold]", border_style="cyan"))
    console.print()

    if not groups_list:
        console.print("[yellow]No groups yet.[/yellow]")
        console.print("[dim]Create one with 'polyterm groups --create <name>'[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Group", width=20)
    table.add_column("Markets", width=10, justify="center")
    table.add_column("Description", max_width=35)

    for group in groups_list:
        table.add_row(
            f"[cyan]{group['name']}[/cyan]",
            str(group['member_count']),
            group.get('description', '')[:33] or "[dim]-[/dim]",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(groups_list)} groups[/dim]")
    console.print()


def _create_group(console: Console, db: Database, name: str, output_format: str):
    """Create a new group"""
    description = ""
    if output_format != 'json':
        description = Prompt.ask("[cyan]Description (optional)[/cyan]", default="")

    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO watchlist_groups (name, description, created_at)
                VALUES (?, ?, ?)
            """, (name, description, datetime.now().isoformat()))
            group_id = cursor.lastrowid

        if output_format == 'json':
            print_json({'success': True, 'action': 'created', 'id': group_id, 'name': name})
        else:
            console.print(f"[green]Group '{name}' created![/green]")
            console.print(f"[dim]Add markets with 'polyterm groups --add \"{name}\" -m <market>'[/dim]")

    except Exception as e:
        if 'UNIQUE' in str(e):
            if output_format == 'json':
                print_json({'success': False, 'error': 'Group already exists'})
            else:
                console.print(f"[yellow]Group '{name}' already exists.[/yellow]")
        else:
            if output_format == 'json':
                print_json({'success': False, 'error': str(e)})
            else:
                console.print(f"[red]Error: {e}[/red]")


def _view_group(console: Console, config, db: Database, name: str, output_format: str):
    """View markets in a group"""
    # Get group
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM watchlist_groups WHERE name = ?", (name,))
        group = cursor.fetchone()

        if not group:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Group not found'})
            else:
                console.print(f"[yellow]Group '{name}' not found.[/yellow]")
            return

        group = dict(group)

        # Get members
        cursor.execute("""
            SELECT * FROM group_members WHERE group_id = ? ORDER BY added_at DESC
        """, (group['id'],))
        members = [dict(row) for row in cursor.fetchall()]

    # Get live prices
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
            progress.add_task("Loading prices...", total=None)

            enriched = []
            for member in members:
                markets = gamma_client.search_markets(member['market_id'], limit=1)
                if markets:
                    market = markets[0]
                    price = _get_price(market)
                    change = _get_price_change(market)
                    enriched.append({
                        **member,
                        'price': price,
                        'change': change,
                    })
                else:
                    enriched.append({**member, 'price': 0, 'change': 0})

    finally:
        gamma_client.close()

    if output_format == 'json':
        print_json({
            'success': True,
            'group': group,
            'members': enriched,
        })
        return

    console.print()
    console.print(Panel(f"[bold]{name}[/bold]\n[dim]{group.get('description', '')}[/dim]", border_style="cyan"))
    console.print()

    if not enriched:
        console.print("[yellow]No markets in this group.[/yellow]")
        console.print(f"[dim]Add with 'polyterm groups --add \"{name}\" -m <market>'[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Market", max_width=45)
    table.add_column("Price", width=8, justify="center")
    table.add_column("24h", width=8, justify="right")

    for member in enriched:
        title = member['title'][:43]
        price_str = f"{member['price']:.0%}" if member['price'] else "-"

        change = member.get('change', 0)
        if change > 0:
            change_str = f"[green]+{change:.1%}[/green]"
        elif change < 0:
            change_str = f"[red]{change:.1%}[/red]"
        else:
            change_str = "[dim]0%[/dim]"

        table.add_row(title, price_str, change_str)

    console.print(table)
    console.print()
    console.print(f"[dim]{len(enriched)} markets in group[/dim]")
    console.print()


def _add_to_group(console: Console, config, db: Database, group_name: str, market_search: str, output_format: str):
    """Add a market to a group"""
    # Get group
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM watchlist_groups WHERE name = ?", (group_name,))
        row = cursor.fetchone()

        if not row:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Group not found'})
            else:
                console.print(f"[yellow]Group '{group_name}' not found.[/yellow]")
            return

        group_id = row['id']

    # Find market
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        markets = gamma_client.search_markets(market_search, limit=1)
        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Market not found'})
            else:
                console.print(f"[yellow]Market '{market_search}' not found.[/yellow]")
            return

        market = markets[0]
        market_id = market.get('id', market.get('condition_id', ''))
        title = market.get('question', market.get('title', ''))

    finally:
        gamma_client.close()

    # Add to group
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO group_members (group_id, market_id, title, added_at)
                VALUES (?, ?, ?, ?)
            """, (group_id, market_id, title, datetime.now().isoformat()))

        if output_format == 'json':
            print_json({'success': True, 'action': 'added', 'group': group_name, 'market': title})
        else:
            console.print(f"[green]Added '{title[:40]}' to {group_name}[/green]")

    except Exception as e:
        if 'UNIQUE' in str(e):
            if output_format == 'json':
                print_json({'success': False, 'error': 'Market already in group'})
            else:
                console.print(f"[yellow]Market already in group.[/yellow]")
        else:
            if output_format == 'json':
                print_json({'success': False, 'error': str(e)})
            else:
                console.print(f"[red]Error: {e}[/red]")


def _remove_from_group(console: Console, db: Database, group_name: str, market_search: str, output_format: str):
    """Remove a market from a group"""
    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Get group
        cursor.execute("SELECT id FROM watchlist_groups WHERE name = ?", (group_name,))
        row = cursor.fetchone()

        if not row:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Group not found'})
            else:
                console.print(f"[yellow]Group '{group_name}' not found.[/yellow]")
            return

        group_id = row['id']

        # Remove matching market
        cursor.execute("""
            DELETE FROM group_members
            WHERE group_id = ? AND (market_id LIKE ? OR title LIKE ?)
        """, (group_id, f'%{market_search}%', f'%{market_search}%'))
        removed = cursor.rowcount

    if output_format == 'json':
        print_json({'success': removed > 0, 'removed': removed})
    else:
        if removed:
            console.print(f"[green]Removed {removed} market(s) from {group_name}[/green]")
        else:
            console.print(f"[yellow]No matching markets found in group.[/yellow]")


def _delete_group(console: Console, db: Database, name: str, output_format: str):
    """Delete a group"""
    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Get group
        cursor.execute("SELECT id FROM watchlist_groups WHERE name = ?", (name,))
        row = cursor.fetchone()

        if not row:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Group not found'})
            else:
                console.print(f"[yellow]Group '{name}' not found.[/yellow]")
            return

        group_id = row['id']

        # Delete members
        cursor.execute("DELETE FROM group_members WHERE group_id = ?", (group_id,))

        # Delete group
        cursor.execute("DELETE FROM watchlist_groups WHERE id = ?", (group_id,))

    if output_format == 'json':
        print_json({'success': True, 'action': 'deleted', 'name': name})
    else:
        console.print(f"[green]Group '{name}' deleted.[/green]")


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                import json
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)


def _get_price_change(market: dict) -> float:
    """Get 24h price change"""
    price_change = market.get('priceChange24h', 0)
    if price_change:
        return price_change

    current = _get_price(market)
    prev = market.get('price24hAgo', 0)
    if prev and prev > 0:
        return (current - prev) / prev

    return 0
