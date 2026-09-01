"""Whales command - wallet-level lagged Data API prints or high-volume market heuristic"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...api.data_api_lag import DISCLOSURE as DATA_API_LAG_DISCLOSURE, label_payload, table_title
from ...api.gamma import GammaClient
from ...core.print_scanner import PrintScanner
from ...core.volume_spikes import DISCLOSURE as VOLUME_DISCLOSURE, EVIDENCE_LEVEL, detect_high_volume_markets
from ...core.wallet_intelligence import WalletIntelligence
from ...core.whale_prints import DEFAULT_PRINT_MIN_NOTIONAL, scan_whale_prints
from ...db.database import Database
from ...utils.json_output import print_json
from ...utils.errors import handle_api_error, show_error


@click.command()
@click.option(
    "--min-amount",
    "--min-notional",
    "min_amount",
    default=DEFAULT_PRINT_MIN_NOTIONAL,
    type=float,
    help=(
        "Minimum 24h Gamma volume (heuristic) or lagged Data API print notional "
        "(--wallets; default $10,000, same as watch/alerts). Not live CLOB."
    ),
)
@click.option("--market", default=None, help="Filter by market ID")
@click.option("--hours", default=24, help="Hours of history for --wallets (timestamp filter on lagged prints)")
@click.option("--limit", default=20, help="Maximum number of rows to show")
@click.option(
    "--wallets",
    is_flag=True,
    help="Wallet-level lagged Data API prints (not live CLOB)",
)
@click.option("--volume", "_volume_heuristic", is_flag=True, help="Gamma 24h high-volume markets (not trader identity)")
@click.option("--local", is_flag=True, help="Use only the local observed-trades database (implies --wallets)")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def whales(ctx, min_amount, market, hours, limit, wallets, _volume_heuristic, local, output_format):
    """Track whale activity or high-volume markets

    Default: Gamma 24h high-volume MARKET heuristic. This is not whale
    identity. It does not invent trader addresses.

    Use --wallets for wallet-level lagged Data API prints with real
    addresses. Those fills are lagged Data API rows, not the live CLOB tape.
    Empty tape stays empty. This path does not score insiders or copy trades.

    Examples:
        polyterm whales --wallets --min-notional 10000
        polyterm whales --volume --min-amount 10000
    """

    config = ctx.obj["config"]
    console = Console()

    if local:
        wallets = True

    if wallets:
        if local:
            intelligence = WalletIntelligence(database=Database())
            result = intelligence.local_whales(min_notional=min_amount, hours=hours)
            result["wallets"] = result["wallets"][:limit]
            _emit_local_wallets(console, result, hours, output_format)
            return

        try:
            result = label_payload(
                scan_whale_prints(
                    scanner=PrintScanner(),
                    min_notional=min_amount,
                    market=market,
                    hours=hours,
                    limit=limit,
                )
            )
        except Exception as e:
            if output_format == "json":
                print_json({
                    "success": False,
                    "error": str(e),
                    "mode": "wallet_trades",
                    "source": "data_api",
                    "lag": True,
                    "lagged": True,
                })
            else:
                handle_api_error(console, e, "listing lagged Data API prints")
            return

        if output_format == "json":
            print_json({"success": True, "mode": "wallet_trades", **result})
            return

        _emit_wallet_prints_table(console, result, hours, min_amount)
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    if output_format != "json":
        console.print(Panel(f"[yellow]{VOLUME_DISCLOSURE}[/yellow]", border_style="yellow"))
        console.print(f"[cyan]High-volume markets ≥ ${min_amount:,.0f} 24h Gamma volume[/cyan]\n")

    try:
        markets = detect_high_volume_markets(gamma_client, min_volume=min_amount)
        if market:
            markets = [item for item in markets if item.market_id == market]
        markets = markets[:limit]

        if output_format == "json":
            total_volume = sum(item.volume_24hr for item in markets)
            print_json({
                "success": True,
                "mode": "volume_heuristic",
                "evidence_level": EVIDENCE_LEVEL,
                "disclosure": VOLUME_DISCLOSURE,
                "timestamp": datetime.now().isoformat(),
                "min_amount": min_amount,
                "hours": hours,
                "count": len(markets),
                "total_volume": total_volume,
                "markets": [item.to_dict() for item in markets],
            })
            return

        if not markets:
            show_error(console, "no_whales_found")
            return

        table = Table(title="High Volume Markets (24h Gamma volume heuristic)")
        table.add_column("Market", style="green", no_wrap=False, max_width=50)
        table.add_column("Trend", justify="center")
        table.add_column("Last Price", justify="right")
        table.add_column("24h Volume", justify="right", style="bold yellow")

        for item in markets:
            if item.outcome_lean == "YES":
                trend_style = "green"
            elif item.outcome_lean == "NO":
                trend_style = "red"
            elif item.outcome_lean == "MIXED":
                trend_style = "yellow"
            else:
                trend_style = "dim"
            trend_text = f"[{trend_style}]{item.outcome_lean}[/{trend_style}]"
            table.add_row(
                item.market_title[:50],
                trend_text,
                f"${item.last_price:.3f}" if item.last_price > 0 else "[dim]N/A[/dim]",
                f"${item.volume_24hr:,.0f}",
            )

        console.print(table)
        total_volume = sum(item.volume_24hr for item in markets)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  High-volume markets: {len(markets)}")
        console.print(f"  Total 24hr volume: ${total_volume:,.0f}")
        console.print(f"  Average per market: ${total_volume/len(markets):,.0f}")
        console.print("\n[dim]For wallet-level lagged Data API prints: polyterm whales --wallets[/dim]")

    except Exception as e:
        if output_format == "json":
            print_json({"success": False, "error": str(e), "mode": "volume_heuristic"})
        else:
            handle_api_error(console, e, "listing high-volume markets")
    finally:
        gamma_client.close()


def _emit_local_wallets(console, result, hours, output_format):
    if output_format == "json":
        print_json({"success": True, "mode": "wallet_trades", **result})
        return

    whale_title = f"Wallet-Level Whale Activity (Last {hours}h)"
    table = Table(title=whale_title)
    table.add_column("Wallet", style="cyan")
    table.add_column("Trades", justify="right")
    table.add_column("Notional", justify="right", style="yellow")
    table.add_column("Largest", justify="right")
    table.add_column("Top Markets", style="dim")
    for wallet in result["wallets"]:
        table.add_row(
            wallet["address"][:14] + "...",
            str(wallet["trade_count"]),
            f"${wallet['notional']:,.0f}",
            f"${wallet['largest_trade']:,.0f}",
            ", ".join(market_id for market_id, _ in wallet["top_markets"][:3]),
        )
    if result["wallets"]:
        console.print(table)
    else:
        console.print("[yellow]No wallet-level whale trades found.[/yellow]")
    console.print(f"[dim]Quality flags: {', '.join(result['quality_flags'])}[/dim]")


def _emit_wallet_prints_table(console, result, hours, min_amount):
    console.print(Panel(f"[yellow]{DATA_API_LAG_DISCLOSURE}[/yellow]", border_style="yellow"))

    prints = result.get("prints") or []
    title = table_title(f"Lagged Data API prints (Last {hours}h, min ${min_amount:,.0f})")
    table = Table(title=title)
    table.add_column("Time", style="dim")
    table.add_column("Wallet", style="cyan")
    table.add_column("Side", justify="center")
    table.add_column("Notional", justify="right", style="yellow")
    table.add_column("Market", style="green", no_wrap=False, max_width=40)

    if not prints:
        console.print("[yellow]No lagged Data API prints matched.[/yellow]")
        console.print(
            "[dim]Empty Data API tape is not invented whales. "
            "lagged Data API, not live CLOB[/dim]"
        )
        console.print(f"[dim]Quality flags: {', '.join(result.get('quality_flags') or [])}[/dim]")
        return

    for row in prints:
        table.add_row(
            str(row.get("timestamp_iso") or row.get("timestamp") or "unknown"),
            str(row.get("wallet") or "unknown"),
            str(row.get("side") or "unknown"),
            _format_notional(row.get("notional")),
            str(
                row.get("market_title")
                or row.get("market_slug")
                or row.get("market_id")
                or row.get("condition_id")
                or "unknown"
            ),
        )
    console.print(table)
    console.print(
        f"[dim]Prints: {len(prints)}  Wallets in tape: {result.get('wallet_count', 0)}  "
        f"lagged Data API, not live CLOB[/dim]"
    )
    console.print(f"[dim]Quality flags: {', '.join(result.get('quality_flags') or [])}[/dim]")


def _format_notional(value):
    if value is None:
        return "unknown"
    try:
        return "${:,.0f}".format(float(value))
    except (TypeError, ValueError):
        return "unknown"
