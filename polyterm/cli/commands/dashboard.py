"""Dashboard command - Quick overview of market activity"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def dashboard(ctx, output_format):
    """Quick overview of market activity

    Shows:
    - Top movers (biggest price changes)
    - Highest volume markets
    - Your bookmarks status
    - Alert summary

    Perfect for a quick morning check or end-of-day review.
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        if output_format != 'json':
            console.print()
            console.print(Panel(
                f"[bold]PolyTerm Dashboard[/bold]\n"
                f"[dim]{datetime.now().strftime('%A, %B %d, %Y %H:%M')}[/dim]",
                border_style="cyan",
            ))
            console.print()

        # Gather data
        markets = gamma_client.get_markets(limit=50, active=True, closed=False)

        # Sort by volume for top markets
        top_volume = sorted(
            markets,
            key=lambda m: float(m.get('volume24hr', 0) or 0),
            reverse=True
        )[:5]

        # Get bookmarks
        bookmarks = db.get_bookmarks()

        # Get alerts
        alerts = db.get_unacknowledged_alerts(limit=5)

        # Get database stats
        db_stats = db.get_database_stats()

        if output_format == 'json':
            print_json({
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'top_volume_markets': [
                    {
                        'id': m.get('id'),
                        'title': m.get('question', m.get('title', '')),
                        'volume_24h': float(m.get('volume24hr', 0) or 0),
                    }
                    for m in top_volume
                ],
                'bookmarks_count': len(bookmarks),
                'unread_alerts': len(alerts),
                'database_stats': db_stats,
            })
            return

        # Top Volume Markets section
        console.print("[bold yellow]Top Volume Markets (24h)[/bold yellow]")
        vol_table = Table(show_header=True, box=None, padding=(0, 1))
        vol_table.add_column("#", style="dim", width=3)
        vol_table.add_column("Market", style="cyan", max_width=45)
        vol_table.add_column("Volume", justify="right", style="yellow")
        vol_table.add_column("Prob", justify="right")

        for i, m in enumerate(top_volume, 1):
            title = m.get('question', m.get('title', ''))[:45]
            volume = float(m.get('volume24hr', 0) or 0)

            # Get probability
            outcome_prices = m.get('outcomePrices', [])
            if isinstance(outcome_prices, str):
                import json
                try:
                    outcome_prices = json.loads(outcome_prices)
                except Exception:
                    outcome_prices = []
            prob = float(outcome_prices[0]) * 100 if outcome_prices else 0

            prob_color = "green" if prob > 50 else "yellow" if prob > 30 else "white"

            vol_table.add_row(
                str(i),
                title,
                f"${volume:,.0f}",
                f"[{prob_color}]{prob:.0f}%[/{prob_color}]",
            )

        console.print(vol_table)
        console.print()

        # Quick stats row
        stats_panels = []

        # Bookmarks panel
        bookmark_text = Text()
        if bookmarks:
            bookmark_text.append(f"{len(bookmarks)}", style="bold cyan")
            bookmark_text.append(" saved", style="dim")
        else:
            bookmark_text.append("None yet", style="dim")
        stats_panels.append(Panel(bookmark_text, title="Bookmarks", width=20))

        # Alerts panel
        alert_text = Text()
        if alerts:
            alert_text.append(f"{len(alerts)}", style="bold yellow")
            alert_text.append(" unread", style="dim")
        else:
            alert_text.append("All clear", style="green")
        stats_panels.append(Panel(alert_text, title="Alerts", width=20))

        # Followed wallets panel
        followed = db.get_followed_wallets()
        follow_text = Text()
        if followed:
            follow_text.append(f"{len(followed)}", style="bold cyan")
            follow_text.append(f"/{10}", style="dim")
        else:
            follow_text.append("None yet", style="dim")
        stats_panels.append(Panel(follow_text, title="Following", width=20))

        # Database panel
        total_records = sum(db_stats.values())
        db_text = Text()
        db_text.append(f"{total_records:,}", style="bold")
        db_text.append(" records", style="dim")
        stats_panels.append(Panel(db_text, title="Data", width=20))

        console.print(Columns(stats_panels))
        console.print()

        # Bookmarks status (if any)
        if bookmarks:
            console.print("[bold yellow]Your Bookmarks[/bold yellow]")
            bm_table = Table(show_header=False, box=None, padding=(0, 1))
            bm_table.add_column(style="cyan", max_width=50)
            bm_table.add_column(style="dim", max_width=20)

            for b in bookmarks[:5]:
                title = b['title'][:50]
                notes = b.get('notes', '')[:20] if b.get('notes') else ''
                bm_table.add_row(title, notes or '-')

            console.print(bm_table)
            if len(bookmarks) > 5:
                console.print(f"[dim]  ... and {len(bookmarks) - 5} more[/dim]")
            console.print()

        # Unread alerts (if any)
        if alerts:
            console.print("[bold yellow]Recent Alerts[/bold yellow]")
            for alert in alerts[:3]:
                severity_color = "red" if alert.severity >= 3 else "yellow" if alert.severity >= 2 else "dim"
                console.print(f"  [{severity_color}]![/{severity_color}] {alert.message[:60]}")
            if len(alerts) > 3:
                console.print(f"[dim]  ... and {len(alerts) - 3} more[/dim]")
            console.print()

        # Quick actions
        console.print("[bold]Quick Actions[/bold]")
        console.print("  [cyan]polyterm monitor[/cyan] - Live market feed")
        console.print("  [cyan]polyterm arbitrage[/cyan] - Scan for opportunities")
        console.print("  [cyan]polyterm predict[/cyan] - Get predictions")
        console.print("  [cyan]polyterm bookmarks[/cyan] - Manage saved markets")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
