"""Leaderboard Command - View top traders and rankings"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...api.data_api import DataAPIClient
from ...db.database import Database
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error


@click.command()
@click.option("--type", "-t", "board_type", type=click.Choice(["profit", "volume", "winrate", "active"]),
              default="profit", help="Leaderboard type")
@click.option("--period", "-p", type=click.Choice(["24h", "7d", "30d", "all"]), default="7d", help="Time period")
@click.option("--limit", "-l", type=int, default=20, help="Number of traders to show")
@click.option("--me", is_flag=True, help="Show your ranking")
@click.option("--source", type=click.Choice(["data-api", "local"]), default="data-api", help="Leaderboard data source")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def leaderboard(ctx, board_type, period, limit, me, source, output_format):
    """View top traders and your ranking

    See the best performers on Polymarket and compare
    your performance to the field.

    Types:
        profit  - Top by realized profit
        volume  - Top by trading volume
        winrate - Top by win percentage
        active  - Most active traders

    Examples:
        polyterm leaderboard                  # Top by profit
        polyterm leaderboard -t winrate       # Top by win rate
        polyterm leaderboard --me             # Your ranking
        polyterm leaderboard -p 24h -l 50     # Daily, 50 traders
    """
    console = Console()
    config = ctx.obj["config"]

    gamma = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    data_api = DataAPIClient()

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Fetching leaderboard data...", total=None)

            if source == "data-api":
                traders = _fetch_data_api_leaderboard(data_api, board_type, period, limit)
            else:
                traders = _build_local_trader_stats(Database(), limit=limit)

        # Sort by type
        if board_type == "profit":
            traders.sort(key=lambda x: x['profit'], reverse=True)
        elif board_type == "volume":
            traders.sort(key=lambda x: x['volume'], reverse=True)
        elif board_type == "winrate":
            traders.sort(key=lambda x: x['win_rate'], reverse=True)
        elif board_type == "active":
            traders.sort(key=lambda x: x['trades'], reverse=True)

        traders = traders[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'type': board_type,
                'period': period,
                'source': source,
                'traders': traders,
            })
            return

        # Display leaderboard
        console.print()

        title_map = {
            "profit": "Top Traders by Profit",
            "volume": "Top Traders by Volume",
            "winrate": "Top Traders by Win Rate",
            "active": "Most Active Traders",
        }

        console.print(Panel(f"[bold]{title_map[board_type]}[/bold] ({period})", border_style="cyan"))
        console.print()

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Rank", width=5, justify="center")
        table.add_column("Trader", width=15)
        table.add_column("Profit", width=12, justify="right")
        table.add_column("Volume", width=12, justify="right")
        table.add_column("Trades", width=8, justify="center")
        table.add_column("Win Rate", width=10, justify="center")
        table.add_column("Avg Size", width=12, justify="right")

        for i, trader in enumerate(traders, 1):
            # Rank styling
            if i == 1:
                rank = "[yellow]1[/yellow]"
            elif i == 2:
                rank = "[white]2[/white]"
            elif i == 3:
                rank = "[bright_black]3[/bright_black]"
            else:
                rank = str(i)

            profit_color = "green" if trader['profit'] > 0 else "red"

            table.add_row(
                rank,
                trader['address'][:12] + "...",
                f"[{profit_color}]${trader['profit']:+,.0f}[/{profit_color}]",
                f"${trader['volume']:,.0f}",
                str(trader['trades']),
                f"{trader['win_rate']:.0%}",
                f"${trader['avg_size']:,.0f}",
            )

        console.print(table)
        console.print()

        # Show your ranking if requested
        if me:
            _show_my_ranking(console, traders)

        # Stats summary
        if traders:
            console.print("[bold]Leaderboard Stats:[/bold]")
            console.print()

            total_profit = sum(t['profit'] for t in traders)
            total_volume = sum(t['volume'] for t in traders)
            avg_win_rate = sum(t['win_rate'] for t in traders) / len(traders)

            console.print(f"  Top {len(traders)} traders combined:")
            console.print(f"    Total Profit: [green]${total_profit:,.0f}[/green]")
            console.print(f"    Total Volume: ${total_volume:,.0f}")
            console.print(f"    Avg Win Rate: {avg_win_rate:.0%}")
            console.print()

        # Tips
        console.print("[dim]Tip: Study top traders' activity with 'polyterm follow --add <address>'[/dim]")
        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            handle_api_error(console, e, "leaderboard")
    finally:
        gamma.close()
        data_api.close()


def _fetch_data_api_leaderboard(data_api: DataAPIClient, board_type: str, period: str, limit: int) -> list:
    """Fetch and normalize leaderboard rows from the public Data API."""
    rows = data_api.get_leaderboard(period=period, limit=limit, sort_by=board_type)
    traders = []
    for row in rows[:limit]:
        address = row.get("address") or row.get("user") or row.get("proxyWallet") or row.get("wallet") or ""
        traders.append({
            "address": address,
            "profit": float(row.get("profit") or row.get("pnl") or row.get("cashPnl") or 0),
            "volume": float(row.get("volume") or row.get("totalVolume") or 0),
            "trades": int(row.get("trades") or row.get("tradeCount") or 0),
            "win_rate": float(row.get("winRate") or row.get("win_rate") or 0),
            "avg_size": float(row.get("avgSize") or row.get("averageTradeSize") or 0),
        })
    return traders


def _build_local_trader_stats(db: Database, limit: int = 20) -> list:
    """Build a real local leaderboard from tracked wallets."""
    wallets = db.get_all_wallets(limit=limit)
    return [
        {
            "address": wallet.address,
            "profit": 0.0,
            "volume": wallet.total_volume,
            "trades": wallet.total_trades,
            "win_rate": wallet.win_rate,
            "avg_size": wallet.avg_position_size,
        }
        for wallet in wallets
    ]


def _show_my_ranking(console: Console, traders: list):
    """Show user's ranking compared to leaderboard"""
    db = Database()

    console.print("[bold]Your Performance:[/bold]")
    console.print()

    # Get user's positions
    positions = db.get_all_positions()

    if not positions:
        console.print("  [yellow]No positions tracked. Add positions to see your ranking.[/yellow]")
        console.print("  [dim]Use 'polyterm position --add' to track trades.[/dim]")
        console.print()
        return

    # Calculate user stats
    total_pnl = 0
    total_volume = 0
    wins = 0
    total_trades = len(positions)

    for pos in positions:
        pnl = float(pos.get('pnl', 0) or 0)
        entry = float(pos.get('entry_price', 0) or 0)
        shares = float(pos.get('shares', 0) or 0)

        total_pnl += pnl
        total_volume += entry * shares

        if pnl > 0:
            wins += 1

    win_rate = wins / total_trades if total_trades > 0 else 0
    avg_size = total_volume / total_trades if total_trades > 0 else 0

    # Find ranking
    profit_rank = 1
    for t in traders:
        if t['profit'] > total_pnl:
            profit_rank += 1

    volume_rank = 1
    for t in traders:
        if t['volume'] > total_volume:
            volume_rank += 1

    # Display
    pnl_color = "green" if total_pnl > 0 else "red"

    console.print(f"  Profit: [{pnl_color}]${total_pnl:+,.0f}[/{pnl_color}] (Rank #{profit_rank})")
    console.print(f"  Volume: ${total_volume:,.0f} (Rank #{volume_rank})")
    console.print(f"  Trades: {total_trades}")
    console.print(f"  Win Rate: {win_rate:.0%}")
    console.print(f"  Avg Size: ${avg_size:,.0f}")
    console.print()

    # Percentile
    if traders:
        percentile = 100 - (profit_rank / len(traders) * 100)
        console.print(f"  You're in the [cyan]top {100 - percentile:.0f}%[/cyan] of traders")
        console.print()
