"""Rewards command - View estimated holding and liquidity rewards"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from ...core.rewards import RewardsCalculator
from ...db.database import Database
from ...utils.json_output import print_json, safe_float


@click.command()
@click.option("--wallet", "-w", default=None, help="Wallet address to check")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def rewards(ctx, wallet, output_format):
    """View estimated holding and liquidity rewards

    Estimates your 4% APY holding rewards based on qualifying positions.
    Qualifying positions must be priced between 20-80 cents and held 24+ hours.

    Examples:
        polyterm rewards
        polyterm rewards --wallet 0x123...
        polyterm rewards --format json
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()
    calc = RewardsCalculator()

    wallet_address = wallet or config.get("wallet.address")

    try:
        # Get positions from database
        if wallet_address:
            db_positions = db.get_positions(status='open', wallet_address=wallet_address)
        else:
            db_positions = db.get_positions(status='open')

        if not db_positions:
            if output_format == 'json':
                print_json({
                    'success': True,
                    'wallet': wallet_address,
                    'positions': [],
                    'positions_count': 0,
                    'rewards': calc.estimate_holding_rewards([]),
                })
                return
            console.print()
            console.print("[yellow]No open positions found[/yellow]")
            console.print("[dim]Track positions with 'polyterm position --add' to estimate rewards.[/dim]")
            return

        # Convert DB positions to rewards format
        positions = []
        for pos in db_positions:
            entry_price = safe_float(pos.get('entry_price', 0.5))
            shares = safe_float(pos.get('shares', 0))
            value = entry_price * shares

            # Calculate hold hours
            entry_date = pos.get('entry_date', '')
            hold_hours = None
            if entry_date:
                try:
                    from datetime import datetime
                    entry_dt = datetime.fromisoformat(str(entry_date))
                    hold_hours = (datetime.now() - entry_dt).total_seconds() / 3600
                except Exception:
                    pass

            positions.append({
                'title': pos.get('title', ''),
                'value': value,
                'price': entry_price,
                'shares': shares,
                'hold_hours': hold_hours,
                'side': pos.get('side', 'YES'),
            })

        result = calc.estimate_holding_rewards(positions)

        if output_format == 'json':
            print_json({
                'success': True,
                'wallet': wallet_address,
                'rewards': result,
                'positions': positions,
                'positions_count': len(positions),
            })
            return

        console.print()
        console.print(Panel(
            "[bold cyan]Holding Rewards Estimate[/bold cyan]\n\n"
            f"Based on {len(positions)} tracked positions.\n"
            "[dim]Polymarket offers ~4% APY on qualifying positions.[/dim]",
            border_style="cyan"
        ))
        console.print()

        # Summary table
        table = Table(show_header=False, box=None)
        table.add_column(width=30)
        table.add_column(width=15, justify="right")

        table.add_row("Qualifying Positions", f"{result['qualifying_positions']}/{len(positions)}")
        table.add_row("Qualifying Value", f"${result['total_qualifying_value']:,.2f}")
        table.add_row("", "")
        table.add_row("[bold]Estimated Rewards:[/bold]", "")
        table.add_row("  Daily", f"[green]${result['estimated_daily']:.4f}[/green]")
        table.add_row("  Weekly", f"[green]${result['estimated_weekly']:.4f}[/green]")
        table.add_row("  Monthly", f"[green]${result['estimated_monthly']:.2f}[/green]")
        table.add_row("  Yearly", f"[green]${result['estimated_yearly']:.2f}[/green]")
        table.add_row("  APY", f"{result['apy']:.1%}")

        console.print(table)
        console.print()

        if result['non_qualifying_positions'] > 0:
            console.print(f"[dim]{result['non_qualifying_positions']} positions don't qualify "
                        "(price outside 20-80 cent range or held < 24h)[/dim]")
            console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
