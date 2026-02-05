"""Recent Markets - View recently accessed markets"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...db.database import Database
from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--limit", "-l", default=15, help="Number of recent markets to show (default: 15)")
@click.option("--most-viewed", "-m", is_flag=True, help="Sort by view count instead of recency")
@click.option("--clear", "-c", is_flag=True, help="Clear recent history")
@click.option("--open", "-o", "open_market", default=None, help="Open a recent market by number")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def recent(ctx, limit, most_viewed, clear, open_market, output_format):
    """View recently accessed markets

    Shows markets you've recently viewed, searched for, or interacted with.
    Helpful for quickly returning to markets you were researching.

    Examples:
        polyterm recent                   # Show recent markets
        polyterm recent -m                # Show most viewed
        polyterm recent --clear           # Clear history
        polyterm recent -o 1              # Open first market
    """
    console = Console()
    db = Database()

    if clear:
        db.clear_recent_history()
        if output_format == 'json':
            print_json({'success': True, 'message': 'Recent history cleared'})
        else:
            console.print("[green]Recent history cleared.[/green]")
        return

    # Get recent markets
    if most_viewed:
        markets = db.get_most_viewed(limit=limit)
        title = "Most Viewed Markets"
    else:
        markets = db.get_recently_viewed(limit=limit)
        title = "Recently Viewed Markets"

    if not markets:
        if output_format == 'json':
            print_json({'success': True, 'markets': [], 'message': 'No recent history'})
        else:
            console.print("[yellow]No recently viewed markets.[/yellow]")
            console.print("[dim]Markets will appear here as you use polyterm commands.[/dim]")
        return

    # Handle opening a market
    if open_market:
        try:
            idx = int(open_market) - 1
            if 0 <= idx < len(markets):
                market = markets[idx]
                _show_market_details(console, ctx.obj["config"], db, market['market_id'], output_format)
                return
            else:
                console.print(f"[red]Invalid market number. Choose 1-{len(markets)}[/red]")
                return
        except ValueError:
            console.print("[red]Please provide a valid number.[/red]")
            return

    if output_format == 'json':
        print_json({
            'success': True,
            'title': title,
            'markets': markets,
        })
        return

    # Display recent markets
    console.print()
    console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("#", style="dim", width=3)
    table.add_column("Market", max_width=50)
    table.add_column("Price", justify="right", width=8)
    table.add_column("Views", justify="right", width=6)
    table.add_column("Last Viewed", width=16)

    for i, m in enumerate(markets, 1):
        # Format last viewed time
        try:
            viewed = datetime.fromisoformat(m['viewed_at'])
            now = datetime.now()
            diff = now - viewed

            if diff.days > 0:
                time_str = f"{diff.days}d ago"
            elif diff.seconds >= 3600:
                time_str = f"{diff.seconds // 3600}h ago"
            elif diff.seconds >= 60:
                time_str = f"{diff.seconds // 60}m ago"
            else:
                time_str = "just now"
        except Exception:
            time_str = m.get('viewed_at', 'Unknown')[:16]

        # Truncate title
        title_str = m.get('title', 'Unknown')[:48]

        table.add_row(
            str(i),
            title_str,
            f"{m.get('probability', 0) * 100:.0f}%",
            str(m.get('view_count', 1)),
            time_str,
        )

    console.print(table)
    console.print()

    # Interactive prompt
    console.print("[dim]Enter a number to view market details, or press Enter to exit[/dim]")
    choice = Prompt.ask("[cyan]Select market[/cyan]", default="")

    if choice:
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(markets):
                market = markets[idx]
                _show_market_details(console, ctx.obj["config"], db, market['market_id'], "table")
        except ValueError:
            pass


def _show_market_details(console: Console, config, db: Database, market_id: str, output_format: str):
    """Show details for a specific market"""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Get market details
        market = gamma_client.get_market(market_id)

        if not market:
            console.print(f"[yellow]Market not found: {market_id}[/yellow]")
            return

        title = market.get('question', market.get('title', 'Unknown'))

        # Get current price
        import json
        outcome_prices = market.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []

        current_price = float(outcome_prices[0]) if outcome_prices else 0.5
        volume = float(market.get('volume', 0) or 0)
        liquidity = float(market.get('liquidity', 0) or 0)

        # Track this view
        db.track_market_view(market_id, title[:100], current_price)

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'price': current_price,
                'volume': volume,
                'liquidity': liquidity,
            })
            return

        console.print()
        console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
        console.print()

        # Market stats
        console.print("[bold yellow]Market Stats[/bold yellow]")
        console.print(f"  ID: [dim]{market_id[:20]}...[/dim]")
        console.print(f"  Price: [cyan]{current_price * 100:.1f}%[/cyan]")

        if volume >= 1_000_000:
            vol_str = f"${volume/1_000_000:.1f}M"
        elif volume >= 1_000:
            vol_str = f"${volume/1_000:.0f}K"
        else:
            vol_str = f"${volume:.0f}"
        console.print(f"  Volume: [green]{vol_str}[/green]")

        if liquidity >= 1_000_000:
            liq_str = f"${liquidity/1_000_000:.1f}M"
        elif liquidity >= 1_000:
            liq_str = f"${liquidity/1_000:.0f}K"
        else:
            liq_str = f"${liquidity:.0f}"
        console.print(f"  Liquidity: [cyan]{liq_str}[/cyan]")

        # End date
        end_date = market.get('endDate', '')
        if end_date:
            console.print(f"  End date: [dim]{end_date[:10]}[/dim]")

        console.print()

        # Quick actions
        console.print("[bold yellow]Quick Actions[/bold yellow]")
        console.print(f"  [dim]polyterm chart -m \"{title[:30]}\"[/dim] - View price history")
        console.print(f"  [dim]polyterm orderbook -m \"{title[:30]}\"[/dim] - View order book")
        console.print(f"  [dim]polyterm bookmarks --add \"{market_id}\"[/dim] - Bookmark this market")
        console.print()

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
