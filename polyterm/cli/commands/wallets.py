"""Wallets command - smart money and whale wallet tracking"""

import click
from datetime import datetime
from rich.console import Console
from rich.table import Table

from ...db.database import Database
from ...db.models import Wallet
from ...core.whale_tracker import InsiderDetector
from ...utils.json_output import print_json


@click.command()
@click.option("--type", "wallet_type", type=click.Choice(["whales", "smart", "suspicious", "all"]), default="whales", help="Type of wallets to show")
@click.option("--limit", default=20, help="Maximum wallets to show")
@click.option("--analyze", default=None, help="Analyze specific wallet address")
@click.option("--track", default=None, help="Add wallet to tracking list")
@click.option("--untrack", default=None, help="Remove wallet from tracking list")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format")
@click.pass_context
def wallets(ctx, wallet_type, limit, analyze, track, untrack, output_format):
    """Track and analyze whale and smart money wallets"""

    config = ctx.obj["config"]
    console = Console()
    db = Database()

    try:
        # Handle tracking operations
        if track:
            db.add_wallet_tag(track, 'tracked')
            if output_format == 'json':
                print_json({'success': True, 'action': 'tracked', 'address': track})
            else:
                console.print(f"[green]Added {track[:20]}... to tracking list[/green]")
            return

        if untrack:
            db.remove_wallet_tag(untrack, 'tracked')
            if output_format == 'json':
                print_json({'success': True, 'action': 'untracked', 'address': untrack})
            else:
                console.print(f"[yellow]Removed {untrack[:20]}... from tracking list[/yellow]")
            return

        # Analyze specific wallet
        if analyze:
            wallet = db.get_wallet(analyze)
            if not wallet:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Wallet not found'})
                else:
                    console.print(f"[red]Wallet not found: {analyze}[/red]")
                return

            detector = InsiderDetector(db)
            analysis = detector.analyze_wallet(wallet)
            stats = db.get_wallet_stats(analyze)

            if output_format == 'json':
                print_json({
                    'success': True,
                    'wallet': wallet.to_dict(),
                    'insider_analysis': analysis,
                    'stats': stats,
                })
            else:
                console.print(f"\n[bold]Wallet Analysis: {analyze[:30]}...[/bold]\n")
                console.print(f"First Seen: {wallet.first_seen.strftime('%Y-%m-%d')}")
                console.print(f"Total Trades: {wallet.total_trades}")
                console.print(f"Total Volume: ${wallet.total_volume:,.0f}")
                console.print(f"Win Rate: {wallet.win_rate:.0%}")
                console.print(f"Avg Position: ${wallet.avg_position_size:,.0f}")
                console.print(f"Tags: {', '.join(wallet.tags) if wallet.tags else 'None'}")

                console.print(f"\n[bold]Risk Analysis:[/bold]")
                risk_color = "red" if analysis['risk_level'] == 'high' else "yellow" if analysis['risk_level'] == 'medium' else "green"
                console.print(f"Risk Score: [{risk_color}]{analysis['risk_score']}/100[/{risk_color}]")
                console.print(f"Risk Level: [{risk_color}]{analysis['risk_level'].upper()}[/{risk_color}]")

                if analysis['risk_factors']:
                    console.print(f"\nRisk Factors:")
                    for factor in analysis['risk_factors']:
                        console.print(f"  - {factor}")
            return

        # Get wallets by type
        wallets_list = []

        if wallet_type == "whales":
            wallets_list = db.get_whale_wallets()
            title = "Whale Wallets (by Volume)"
        elif wallet_type == "smart":
            wallets_list = db.get_smart_money_wallets()
            title = "Smart Money Wallets (>70% Win Rate)"
        elif wallet_type == "suspicious":
            wallets_list = db.get_suspicious_wallets()
            title = "Suspicious Wallets (High Risk Score)"
        else:
            wallets_list = db.get_all_wallets(limit=limit)
            title = "All Tracked Wallets"

        wallets_list = wallets_list[:limit]

        # JSON output
        if output_format == 'json':
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'type': wallet_type,
                'count': len(wallets_list),
                'wallets': [w.to_dict() for w in wallets_list],
            }
            print_json(output)
            return

        if not wallets_list:
            console.print(f"[yellow]No {wallet_type} wallets found in database[/yellow]")
            console.print("[dim]Wallets are tracked automatically when trades are processed[/dim]")
            return

        # Create table
        table = Table(title=title)

        table.add_column("Address", style="cyan")
        table.add_column("Trades", justify="right")
        table.add_column("Volume", justify="right", style="yellow")
        table.add_column("Win Rate", justify="right")
        table.add_column("Avg Size", justify="right")
        table.add_column("Tags", style="dim")

        for wallet in wallets_list:
            # Win rate color
            wr_color = "green" if wallet.win_rate >= 0.7 else "yellow" if wallet.win_rate >= 0.5 else "white"

            tags_display = ', '.join(wallet.tags[:3]) if wallet.tags else '-'

            table.add_row(
                f"{wallet.address[:12]}...",
                str(wallet.total_trades),
                f"${wallet.total_volume:,.0f}",
                f"[{wr_color}]{wallet.win_rate:.0%}[/{wr_color}]",
                f"${wallet.avg_position_size:,.0f}",
                tags_display,
            )

        console.print(table)

        # Summary
        total_volume = sum(w.total_volume for w in wallets_list)
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(f"  Wallets shown: {len(wallets_list)}")
        console.print(f"  Total volume: ${total_volume:,.0f}")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
