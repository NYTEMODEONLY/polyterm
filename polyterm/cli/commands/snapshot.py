"""Market Snapshot - Save and compare market states over time"""

import click
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--save", "-s", "save_market", default=None, help="Save snapshot of a market")
@click.option("--list", "-l", "list_snapshots", is_flag=True, help="List saved snapshots")
@click.option("--view", "-v", type=int, default=None, help="View snapshot by ID")
@click.option("--compare", "-c", type=int, default=None, help="Compare snapshot to current state")
@click.option("--delete", "-d", type=int, default=None, help="Delete snapshot")
@click.option("--market", "-m", default=None, help="Filter by market")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def snapshot(ctx, save_market, list_snapshots, view, compare, delete, market, output_format):
    """Save and compare market states over time

    Take snapshots of market data to track how they evolve.
    Compare past snapshots to current state.

    Examples:
        polyterm snapshot --save "bitcoin"       # Save current state
        polyterm snapshot --list                 # List snapshots
        polyterm snapshot --compare 1            # Compare snapshot #1 to now
        polyterm snapshot --view 1               # View snapshot details
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Initialize snapshot table
    _init_snapshot_table(db)

    # Delete snapshot
    if delete:
        _delete_snapshot(console, db, delete, output_format)
        return

    # View snapshot
    if view:
        _view_snapshot(console, db, view, output_format)
        return

    # Compare snapshot
    if compare:
        _compare_snapshot(console, config, db, compare, output_format)
        return

    # Save snapshot
    if save_market:
        _save_snapshot(console, config, db, save_market, output_format)
        return

    # List snapshots
    _list_snapshots(console, db, market, output_format)


def _init_snapshot_table(db: Database):
    """Initialize snapshot table"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_snapshots_v2 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                title TEXT NOT NULL,
                price REAL NOT NULL,
                volume_24h REAL DEFAULT 0,
                volume_total REAL DEFAULT 0,
                liquidity REAL DEFAULT 0,
                data TEXT NOT NULL,
                note TEXT DEFAULT '',
                created_at TIMESTAMP NOT NULL
            )
        """)


def _list_snapshots(console: Console, db: Database, market_filter: str, output_format: str):
    """List all snapshots"""
    with db._get_connection() as conn:
        cursor = conn.cursor()

        if market_filter:
            cursor.execute("""
                SELECT * FROM market_snapshots_v2
                WHERE title LIKE ? OR market_id LIKE ?
                ORDER BY created_at DESC
            """, (f'%{market_filter}%', f'%{market_filter}%'))
        else:
            cursor.execute("""
                SELECT * FROM market_snapshots_v2 ORDER BY created_at DESC LIMIT 50
            """)

        snapshots = [dict(row) for row in cursor.fetchall()]

    if output_format == 'json':
        print_json({'success': True, 'count': len(snapshots), 'snapshots': snapshots})
        return

    console.print()
    console.print(Panel("[bold]Market Snapshots[/bold]", border_style="cyan"))
    console.print()

    if not snapshots:
        console.print("[yellow]No snapshots saved.[/yellow]")
        console.print("[dim]Save one with 'polyterm snapshot --save <market>'[/dim]")
        return

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", width=4)
    table.add_column("Date", width=12)
    table.add_column("Market", max_width=40)
    table.add_column("Price", width=8, justify="center")

    for snap in snapshots:
        try:
            date = datetime.fromisoformat(snap['created_at']).strftime("%m/%d %H:%M")
        except Exception:
            date = snap['created_at'][:10]

        table.add_row(
            str(snap['id']),
            date,
            snap['title'][:38],
            f"{snap['price']:.0%}",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(snapshots)} snapshots[/dim]")
    console.print("[dim]Compare with: polyterm snapshot --compare <id>[/dim]")
    console.print()


def _save_snapshot(console: Console, config, db: Database, search_term: str, output_format: str):
    """Save a market snapshot"""
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
            progress.add_task("Saving snapshot...", total=None)

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
            volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
            volume_total = market.get('volume', 0) or 0
            liquidity = market.get('liquidity', 0) or 0

            # Save to database
            with db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO market_snapshots_v2
                    (market_id, title, price, volume_24h, volume_total, liquidity, data, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    market_id, title, price, volume_24h, volume_total, liquidity,
                    json.dumps(market), datetime.now().isoformat()
                ))
                snapshot_id = cursor.lastrowid

    finally:
        gamma_client.close()

    if output_format == 'json':
        print_json({'success': True, 'id': snapshot_id, 'market': title, 'price': price})
    else:
        console.print(f"[green]Snapshot #{snapshot_id} saved![/green]")
        console.print(f"[dim]{title[:50]}[/dim]")
        console.print(f"[dim]Price: {price:.1%}[/dim]")


def _view_snapshot(console: Console, db: Database, snapshot_id: int, output_format: str):
    """View snapshot details"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM market_snapshots_v2 WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()

    if not row:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Snapshot not found'})
        else:
            console.print(f"[yellow]Snapshot #{snapshot_id} not found.[/yellow]")
        return

    snap = dict(row)

    if output_format == 'json':
        print_json({'success': True, 'snapshot': snap})
        return

    console.print()
    console.print(Panel(f"[bold]Snapshot #{snapshot_id}[/bold]", border_style="cyan"))
    console.print()

    console.print(f"[bold]{snap['title']}[/bold]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(width=15)
    table.add_column(justify="right")

    table.add_row("Price", f"{snap['price']:.1%}")
    table.add_row("24h Volume", f"${snap['volume_24h']:,.0f}")
    table.add_row("Total Volume", f"${snap['volume_total']:,.0f}")
    table.add_row("Liquidity", f"${snap['liquidity']:,.0f}")

    console.print(table)
    console.print()

    try:
        created = datetime.fromisoformat(snap['created_at']).strftime("%Y-%m-%d %H:%M")
        console.print(f"[dim]Captured: {created}[/dim]")
    except Exception:
        pass

    console.print()


def _compare_snapshot(console: Console, config, db: Database, snapshot_id: int, output_format: str):
    """Compare snapshot to current state"""
    # Get snapshot
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM market_snapshots_v2 WHERE id = ?", (snapshot_id,))
        row = cursor.fetchone()

    if not row:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Snapshot not found'})
        else:
            console.print(f"[yellow]Snapshot #{snapshot_id} not found.[/yellow]")
        return

    snap = dict(row)

    # Get current data
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        markets = gamma_client.search_markets(snap['market_id'], limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Market no longer exists'})
            else:
                console.print("[yellow]Market no longer exists.[/yellow]")
            return

        market = markets[0]
        current_price = _get_price(market)
        current_volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
        current_volume_total = market.get('volume', 0) or 0
        current_liquidity = market.get('liquidity', 0) or 0

    finally:
        gamma_client.close()

    # Calculate changes
    price_change = current_price - snap['price']
    price_change_pct = price_change / snap['price'] if snap['price'] > 0 else 0

    volume_change = current_volume_total - snap['volume_total']
    volume_change_pct = volume_change / snap['volume_total'] if snap['volume_total'] > 0 else 0

    if output_format == 'json':
        print_json({
            'success': True,
            'snapshot': snap,
            'current': {
                'price': current_price,
                'volume_24h': current_volume_24h,
                'volume_total': current_volume_total,
                'liquidity': current_liquidity,
            },
            'changes': {
                'price': price_change,
                'price_pct': price_change_pct,
                'volume': volume_change,
                'volume_pct': volume_change_pct,
            }
        })
        return

    # Display comparison
    console.print()
    console.print(Panel(f"[bold]Snapshot Comparison #{snapshot_id}[/bold]", border_style="cyan"))
    console.print()

    console.print(f"[bold]{snap['title'][:60]}[/bold]")
    console.print()

    # Time since snapshot
    try:
        snap_time = datetime.fromisoformat(snap['created_at'])
        age = datetime.now() - snap_time
        if age.days > 0:
            age_str = f"{age.days} days ago"
        else:
            age_str = f"{age.seconds // 3600} hours ago"
        console.print(f"[dim]Snapshot taken {age_str}[/dim]")
    except Exception:
        pass

    console.print()

    # Comparison table
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("", width=15)
    table.add_column("Then", width=12, justify="right")
    table.add_column("Now", width=12, justify="right")
    table.add_column("Change", width=12, justify="right")

    # Price
    pc_color = "green" if price_change >= 0 else "red"
    table.add_row(
        "Price",
        f"{snap['price']:.1%}",
        f"{current_price:.1%}",
        f"[{pc_color}]{price_change:+.1%}[/{pc_color}]",
    )

    # Volume
    vc_color = "green" if volume_change >= 0 else "red"
    table.add_row(
        "Total Volume",
        f"${snap['volume_total']:,.0f}",
        f"${current_volume_total:,.0f}",
        f"[{vc_color}]{volume_change_pct:+.1%}[/{vc_color}]",
    )

    # Liquidity
    liq_change = current_liquidity - snap['liquidity']
    lc_color = "green" if liq_change >= 0 else "red"
    liq_pct = liq_change / snap['liquidity'] if snap['liquidity'] > 0 else 0
    table.add_row(
        "Liquidity",
        f"${snap['liquidity']:,.0f}",
        f"${current_liquidity:,.0f}",
        f"[{lc_color}]{liq_pct:+.1%}[/{lc_color}]",
    )

    console.print(table)
    console.print()

    # Summary
    if price_change >= 0.05:
        console.print(f"[green]Price up {price_change:.1%} since snapshot[/green]")
    elif price_change <= -0.05:
        console.print(f"[red]Price down {price_change:.1%} since snapshot[/red]")
    else:
        console.print(f"[yellow]Price relatively stable[/yellow]")

    console.print()


def _delete_snapshot(console: Console, db: Database, snapshot_id: int, output_format: str):
    """Delete a snapshot"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM market_snapshots_v2 WHERE id = ?", (snapshot_id,))
        deleted = cursor.rowcount > 0

    if output_format == 'json':
        print_json({'success': deleted})
    else:
        if deleted:
            console.print(f"[green]Snapshot #{snapshot_id} deleted.[/green]")
        else:
            console.print(f"[yellow]Snapshot #{snapshot_id} not found.[/yellow]")


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            prices = market['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return market.get('bestAsk', market.get('lastTradePrice', 0.5))
