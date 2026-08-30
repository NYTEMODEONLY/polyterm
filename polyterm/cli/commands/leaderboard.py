"""Leaderboard Command - View public Data API trader rankings"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ...api.data_api import DataAPIClient
from ...core.leaderboard import (
    DATA_API_ENDPOINT,
    UnsupportedLeaderboardType,
    WINRATE_UNSUPPORTED_MESSAGE,
    data_api_sort_by,
    format_trader_label,
    leaderboard_quality_flags,
    normalize_leaderboard_rows,
    sort_traders,
)
from ...db.database import Database
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error


@click.command()
@click.option("--type", "-t", "board_type", type=click.Choice(["profit", "volume", "winrate", "active"]),
              default="profit", help="Leaderboard type")
@click.option("--period", "-p", type=click.Choice(["24h", "7d", "30d", "all"]), default="7d", help="Time period")
@click.option("--limit", "-l", type=int, default=20, help="Number of traders to show")
@click.option("--me", is_flag=True, help="Show your ranking against this board using local positions")
@click.option("--source", type=click.Choice(["data-api", "local"]), default="data-api", help="Leaderboard data source")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def leaderboard(ctx, board_type, period, limit, me, source, output_format):
    """View public Polymarket trader rankings

    Default source is Data API GET /v1/leaderboard (PNL or VOL).
    That endpoint does not provide win rate, trade count, or average size.
    --type winrate is refused on the Data API source instead of being
    silently mapped to profit.

    --source local ranks wallets already stored in local SQLite. It is
    not a live Polymarket ranking.

    Examples:
        polyterm leaderboard
        polyterm leaderboard -t volume -p 24h
        polyterm leaderboard --source local
        polyterm leaderboard --me
    """
    console = Console()
    data_api = DataAPIClient()

    try:
        if source == "data-api" and board_type == "winrate":
            _emit_unsupported(console, output_format)
            return

        if source == "data-api":
            traders = _fetch_data_api_leaderboard(data_api, board_type, period, limit)
        else:
            traders = _build_local_trader_stats(Database(), limit=limit)

        traders = sort_traders(traders, board_type)[:limit]
        flags = leaderboard_quality_flags(source, board_type, traders)

        if output_format == "json":
            print_json({
                "success": True,
                "type": board_type,
                "period": period,
                "source": source,
                "endpoint": DATA_API_ENDPOINT if source == "data-api" else "local_sqlite",
                "quality_flags": flags,
                "traders": traders,
            })
            return

        _render_table(console, board_type, period, source, flags, traders)

        if me:
            _show_my_ranking(console, traders)

    except UnsupportedLeaderboardType:
        _emit_unsupported(console, output_format)
    except Exception as e:
        if output_format == "json":
            print_json({"success": False, "error": str(e), "source": source})
        else:
            handle_api_error(console, e, "leaderboard")
    finally:
        data_api.close()


def _emit_unsupported(console: Console, output_format: str) -> None:
    if output_format == "json":
        print_json({
            "success": False,
            "error": WINRATE_UNSUPPORTED_MESSAGE,
            "source": "data-api",
            "quality_flags": ["winrate_unsupported_by_public_leaderboard"],
        })
    else:
        console.print(Panel(f"[yellow]{WINRATE_UNSUPPORTED_MESSAGE}[/yellow]", border_style="yellow"))


def _fetch_data_api_leaderboard(data_api: DataAPIClient, board_type: str, period: str, limit: int) -> list:
    """Fetch and normalize leaderboard rows from the public Data API."""
    sort_by = data_api_sort_by(board_type)
    rows = data_api.get_leaderboard(period=period, limit=limit, sort_by=sort_by)
    return normalize_leaderboard_rows(rows, limit=limit)


def _build_local_trader_stats(db: Database, limit: int = 20) -> list:
    """Build a local leaderboard from tracked wallets. Not a live Polymarket ranking."""
    wallets = db.get_all_wallets(limit=limit)
    return [
        {
            "address": wallet.address,
            "user_name": "",
            "profit": None,
            "volume": wallet.total_volume,
            "trades": wallet.total_trades,
            "win_rate": wallet.win_rate,
            "avg_size": wallet.avg_position_size,
            "rank": None,
        }
        for wallet in wallets
    ]


def _render_table(console: Console, board_type: str, period: str, source: str, flags: list, traders: list) -> None:
    console.print()
    title_map = {
        "profit": "Top Traders by Profit",
        "volume": "Top Traders by Volume",
        "winrate": "Top Traders by Win Rate",
        "active": "Most Active Traders (volume ranking)",
    }
    source_label = (
        "Polymarket Data API /v1/leaderboard"
        if source == "data-api"
        else "local tracked wallets (not a live Polymarket ranking)"
    )
    console.print(Panel(
        f"[bold]{title_map[board_type]}[/bold] ({period})\n"
        f"[dim]Source: {source_label}[/dim]",
        border_style="cyan",
    ))
    if "active_ranked_by_volume" in flags:
        console.print("[yellow]Most-active uses volume ranking. Trade counts are not provided by this endpoint.[/yellow]")
    if "win_rate_not_provided" in flags:
        console.print("[dim]Win rate is not provided by /v1/leaderboard and is omitted rather than shown as 0%.[/dim]")
    console.print()

    if not traders:
        console.print("[yellow]No leaderboard rows returned.[/yellow]")
        console.print()
        return

    show_trades = any(t.get("trades") is not None for t in traders)
    show_win = any(t.get("win_rate") is not None for t in traders)
    show_avg = any(t.get("avg_size") is not None for t in traders)

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Rank", width=5, justify="center")
    table.add_column("Trader", width=28)
    table.add_column("Profit", width=12, justify="right")
    table.add_column("Volume", width=12, justify="right")
    if show_trades:
        table.add_column("Trades", width=8, justify="center")
    if show_win:
        table.add_column("Win Rate", width=10, justify="center")
    if show_avg:
        table.add_column("Avg Size", width=12, justify="right")

    for i, trader in enumerate(traders, 1):
        if i == 1:
            rank = "[yellow]1[/yellow]"
        elif i == 2:
            rank = "[white]2[/white]"
        elif i == 3:
            rank = "[bright_black]3[/bright_black]"
        else:
            rank = str(i)

        profit = trader.get("profit")
        if profit is None:
            profit_cell = "—"
        else:
            profit_color = "green" if profit > 0 else "red"
            profit_cell = f"[{profit_color}]${profit:+,.0f}[/{profit_color}]"
        row = [
            rank,
            format_trader_label(trader),
            profit_cell,
            f"${(trader.get('volume') or 0):,.0f}",
        ]
        if show_trades:
            trades = trader.get("trades")
            row.append(str(trades) if trades is not None else "—")
        if show_win:
            win_rate = trader.get("win_rate")
            row.append(f"{win_rate:.0%}" if win_rate is not None else "—")
        if show_avg:
            avg_size = trader.get("avg_size")
            row.append(f"${avg_size:,.0f}" if avg_size is not None else "—")
        table.add_row(*row)

    console.print(table)
    console.print()

    if traders:
        console.print("[bold]Leaderboard Stats:[/bold]")
        console.print()
        profits = [t.get("profit") for t in traders if t.get("profit") is not None]
        total_volume = sum(t.get("volume") or 0 for t in traders)
        console.print(f"  Top {len(traders)} traders combined:")
        if profits:
            console.print(f"    Total Profit: [green]${sum(profits):,.0f}[/green]")
        else:
            console.print("    Total Profit: — (not provided by this source)")
        console.print(f"    Total Volume: ${total_volume:,.0f}")
        console.print()

    console.print("[dim]Tip: Study top traders' activity with 'polyterm follow --add <address>'[/dim]")
    console.print()


def _show_my_ranking(console: Console, traders: list):
    """Compare locally tracked positions to the displayed board. Not a live rank."""
    db = Database()

    console.print("[bold]Your Performance (local positions vs this board):[/bold]")
    console.print()

    positions = db.get_all_positions()

    if not positions:
        console.print("  [yellow]No positions tracked. Add positions to see your ranking.[/yellow]")
        console.print("  [dim]Use 'polyterm position --add' to track trades.[/dim]")
        console.print()
        return

    total_pnl = 0
    total_volume = 0
    wins = 0
    total_trades = len(positions)

    for pos in positions:
        pnl = float(pos.get("pnl", 0) or 0)
        entry = float(pos.get("entry_price", 0) or 0)
        shares = float(pos.get("shares", 0) or 0)

        total_pnl += pnl
        total_volume += entry * shares

        if pnl > 0:
            wins += 1

    win_rate = wins / total_trades if total_trades > 0 else 0
    avg_size = total_volume / total_trades if total_trades > 0 else 0

    profit_rank = 1
    for t in traders:
        if (t.get("profit") or 0) > total_pnl:
            profit_rank += 1

    volume_rank = 1
    for t in traders:
        if (t.get("volume") or 0) > total_volume:
            volume_rank += 1

    pnl_color = "green" if total_pnl > 0 else "red"

    console.print(f"  Profit: [{pnl_color}]${total_pnl:+,.0f}[/{pnl_color}] (Rank #{profit_rank} on this board)")
    console.print(f"  Volume: ${total_volume:,.0f} (Rank #{volume_rank} on this board)")
    console.print(f"  Trades: {total_trades}")
    console.print(f"  Win Rate: {win_rate:.0%}")
    console.print(f"  Avg Size: ${avg_size:,.0f}")
    console.print()
    console.print("[dim]This comparison uses local tracked positions, not a live Polymarket rank.[/dim]")
    console.print()
