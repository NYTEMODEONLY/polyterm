"""Pinned Markets - Quick access to your most important markets"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=False)
@click.option("--unpin", "-u", default=None, help="Unpin a market by ID")
@click.option("--clear", "-c", is_flag=True, help="Clear all pinned markets")
@click.option("--refresh", "-r", is_flag=True, help="Refresh pinned market prices")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def pin(ctx, market_search, unpin, clear, refresh, output_format):
    """Pin markets for quick access

    Your most important markets always one command away.
    Shows current prices and changes at a glance.

    Examples:
        polyterm pin "bitcoin"       # Pin a market
        polyterm pin                 # Show pinned markets
        polyterm pin --unpin 1       # Unpin by ID
        polyterm pin --refresh       # Update all prices
        polyterm pin --clear         # Remove all pins
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Initialize pins table
    _init_pins_table(db)

    # Clear all pins
    if clear:
        _clear_pins(console, db, output_format)
        return

    # Unpin specific market
    if unpin:
        _unpin_market(console, db, unpin, output_format)
        return

    # Pin new market
    if market_search:
        _pin_market(console, config, db, market_search, output_format)
        return

    # Show pinned markets (with optional refresh)
    _show_pinned(console, config, db, refresh, output_format)


def _init_pins_table(db: Database):
    """Initialize pinned markets table"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pinned_markets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                last_price REAL DEFAULT 0.5,
                last_updated TIMESTAMP,
                pinned_at TIMESTAMP NOT NULL,
                sort_order INTEGER DEFAULT 0
            )
        """)


def _pin_market(console: Console, config, db: Database, search_term: str, output_format: str):
    """Pin a new market"""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        markets = gamma_client.search_markets(search_term, limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Market not found'})
            else:
                console.print(f"[yellow]Market '{search_term}' not found.[/yellow]")
            return

        market = markets[0]
        market_id = market.get('id', market.get('condition_id', ''))
        title = market.get('question', market.get('title', ''))
        price = _get_price(market)

    finally:
        gamma_client.close()

    # Get current max sort order
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(sort_order) FROM pinned_markets")
        row = cursor.fetchone()
        max_order = row[0] if row[0] else 0

    # Insert or update
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pinned_markets (market_id, title, last_price, last_updated, pinned_at, sort_order)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(market_id) DO UPDATE SET
                    last_price = excluded.last_price,
                    last_updated = excluded.last_updated
            """, (market_id, title, price, datetime.now().isoformat(), datetime.now().isoformat(), max_order + 1))

        if output_format == 'json':
            print_json({'success': True, 'action': 'pinned', 'market': title, 'price': price})
        else:
            console.print(f"[green]Pinned:[/green] {title[:50]}")
            console.print(f"[dim]Current price: {price:.1%}[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")


def _unpin_market(console: Console, db: Database, pin_id: str, output_format: str):
    """Unpin a market by ID"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pinned_markets WHERE id = ?", (pin_id,))
        deleted = cursor.rowcount > 0

    if output_format == 'json':
        print_json({'success': deleted})
    else:
        if deleted:
            console.print(f"[green]Unpinned market #{pin_id}[/green]")
        else:
            console.print(f"[yellow]Pin #{pin_id} not found.[/yellow]")


def _clear_pins(console: Console, db: Database, output_format: str):
    """Clear all pinned markets"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM pinned_markets")
        deleted = cursor.rowcount

    if output_format == 'json':
        print_json({'success': True, 'cleared': deleted})
    else:
        console.print(f"[green]Cleared {deleted} pinned market(s).[/green]")


def _show_pinned(console: Console, config, db: Database, refresh: bool, output_format: str):
    """Show all pinned markets"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM pinned_markets ORDER BY sort_order, pinned_at DESC
        """)
        pins = [dict(row) for row in cursor.fetchall()]

    if not pins:
        if output_format == 'json':
            print_json({'success': True, 'count': 0, 'pins': []})
        else:
            console.print()
            console.print(Panel("[bold]Pinned Markets[/bold]", border_style="cyan"))
            console.print()
            console.print("[yellow]No pinned markets.[/yellow]")
            console.print("[dim]Pin a market with 'polyterm pin <market>'[/dim]")
        return

    # Refresh prices if requested
    if refresh:
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
                progress.add_task("Refreshing prices...", total=None)

                for pin in pins:
                    try:
                        markets = gamma_client.search_markets(pin['market_id'], limit=1)
                        if markets:
                            new_price = _get_price(markets[0])
                            pin['previous_price'] = pin['last_price']
                            pin['last_price'] = new_price

                            # Update in DB
                            with db._get_connection() as conn:
                                cursor = conn.cursor()
                                cursor.execute("""
                                    UPDATE pinned_markets
                                    SET last_price = ?, last_updated = ?
                                    WHERE id = ?
                                """, (new_price, datetime.now().isoformat(), pin['id']))
                    except Exception:
                        pin['previous_price'] = pin['last_price']

        finally:
            gamma_client.close()
    else:
        for pin in pins:
            pin['previous_price'] = pin['last_price']

    if output_format == 'json':
        print_json({'success': True, 'count': len(pins), 'pins': pins})
        return

    # Display
    console.print()
    console.print(Panel("[bold]Pinned Markets[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", width=3)
    table.add_column("Market", max_width=45)
    table.add_column("Price", width=8, justify="center")
    table.add_column("Change", width=8, justify="right")
    table.add_column("Actions", width=12)

    for pin in pins:
        title = pin['title'][:43]
        price = pin['last_price']
        prev = pin.get('previous_price', price)

        change = price - prev
        if change > 0.001:
            change_str = f"[green]+{change:.1%}[/green]"
        elif change < -0.001:
            change_str = f"[red]{change:.1%}[/red]"
        else:
            change_str = "[dim]0%[/dim]"

        actions = f"[dim]unpin: -u {pin['id']}[/dim]"

        table.add_row(
            str(pin['id']),
            title,
            f"{price:.0%}",
            change_str,
            actions,
        )

    console.print(table)
    console.print()

    # Quick stats
    avg_price = sum(p['last_price'] for p in pins) / len(pins)
    console.print(f"[dim]{len(pins)} pinned | Avg price: {avg_price:.0%}[/dim]")

    if not refresh:
        console.print("[dim]Refresh prices with: polyterm pin --refresh[/dim]")

    console.print()

    # Quick actions
    console.print("[bold]Quick Actions:[/bold]")
    console.print("  [cyan]polyterm pin <market>[/cyan] - Pin new market")
    console.print("  [cyan]polyterm pin --unpin <#>[/cyan] - Remove a pin")
    console.print("  [cyan]polyterm pin --refresh[/cyan] - Update all prices")
    console.print()


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            import json
            prices = market['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))
