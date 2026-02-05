"""Exit Strategy Planner - Plan profit targets and stop losses"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", "search_term", default=None, help="Market to plan exit for")
@click.option("--entry", "-e", type=float, default=None, help="Your entry price (0-1)")
@click.option("--shares", "-s", type=float, default=None, help="Number of shares")
@click.option("--side", type=click.Choice(["yes", "no"]), default="yes", help="Position side")
@click.option("--list", "-l", "list_plans", is_flag=True, help="List saved exit plans")
@click.option("--delete", "-d", type=int, default=None, help="Delete exit plan by ID")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def exit(ctx, search_term, entry, shares, side, list_plans, delete, interactive, output_format):
    """Plan exit strategies with profit targets and stop losses

    Calculates breakeven, profit targets, and risk/reward ratios.
    Saves plans that can be checked against price alerts.

    Examples:
        polyterm exit -m "bitcoin" -e 0.65 -s 100    # Plan exit
        polyterm exit --interactive                   # Interactive mode
        polyterm exit --list                          # View saved plans
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # List saved plans
    if list_plans:
        _list_exit_plans(console, db, output_format)
        return

    # Delete plan
    if delete:
        _delete_exit_plan(console, db, delete, output_format)
        return

    # Interactive mode
    if interactive:
        search_term = Prompt.ask("[cyan]Search for market[/cyan]", default="")
        if not search_term:
            return

    if not search_term:
        console.print("[yellow]Please specify a market with -m or use --interactive[/yellow]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Find market
        markets = gamma_client.search_markets(search_term, limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
            else:
                console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
            return

        market = markets[0]
        market_id = market.get('id', market.get('condition_id', ''))
        title = market.get('question', market.get('title', ''))[:60]
        current_price = _get_price(market)

        # Get entry price
        if entry is None:
            if interactive:
                entry_str = Prompt.ask(
                    f"[cyan]Entry price[/cyan] [dim](current: {current_price:.2f})[/dim]",
                    default=f"{current_price:.2f}"
                )
                try:
                    entry = float(entry_str)
                except ValueError:
                    entry = current_price
            else:
                entry = current_price

        # Get shares
        if shares is None:
            if interactive:
                shares_str = Prompt.ask("[cyan]Number of shares[/cyan]", default="100")
                try:
                    shares = float(shares_str)
                except ValueError:
                    shares = 100
            else:
                shares = 100

        # Get side
        if interactive:
            side = Prompt.ask(
                "[cyan]Position side[/cyan]",
                choices=["yes", "no"],
                default="yes"
            )

        # Calculate exit strategy
        strategy = _calculate_exit_strategy(entry, shares, side, current_price)

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'current_price': current_price,
                'position': {
                    'entry': entry,
                    'shares': shares,
                    'side': side,
                    'cost_basis': strategy['cost_basis'],
                },
                'strategy': strategy,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
        console.print()

        # Position summary
        console.print("[bold]Position Summary:[/bold]")
        console.print(f"  Side: [{'green' if side == 'yes' else 'red'}]{side.upper()}[/{'green' if side == 'yes' else 'red'}]")
        console.print(f"  Entry: {entry:.2f} ({entry:.0%})")
        console.print(f"  Shares: {shares:,.0f}")
        console.print(f"  Cost Basis: ${strategy['cost_basis']:,.2f}")
        console.print(f"  Current: {current_price:.2f} ({current_price:.0%})")
        console.print()

        # Current P&L
        pnl_color = "green" if strategy['current_pnl'] >= 0 else "red"
        console.print(f"[bold]Current P&L:[/bold] [{pnl_color}]${strategy['current_pnl']:+,.2f} ({strategy['current_pnl_pct']:+.1%})[/{pnl_color}]")
        console.print()

        # Exit targets table
        console.print("[bold]Exit Strategy:[/bold]")
        console.print()

        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Target", width=15)
        table.add_column("Price", width=10, justify="center")
        table.add_column("P&L", width=12, justify="right")
        table.add_column("ROI", width=10, justify="right")
        table.add_column("R:R", width=8, justify="center")

        # Stop loss levels
        for sl in strategy['stop_losses']:
            table.add_row(
                f"[red]{sl['label']}[/red]",
                f"{sl['price']:.2f}",
                f"[red]${sl['pnl']:,.2f}[/red]",
                f"[red]{sl['roi']:.1%}[/red]",
                "-",
            )

        # Breakeven
        table.add_row(
            "[yellow]Breakeven[/yellow]",
            f"{strategy['breakeven']:.2f}",
            "$0.00",
            "0%",
            "-",
        )

        # Take profit levels
        for tp in strategy['take_profits']:
            rr = abs(tp['pnl'] / strategy['stop_losses'][0]['pnl']) if strategy['stop_losses'][0]['pnl'] != 0 else 0
            table.add_row(
                f"[green]{tp['label']}[/green]",
                f"{tp['price']:.2f}",
                f"[green]+${tp['pnl']:,.2f}[/green]",
                f"[green]+{tp['roi']:.1%}[/green]",
                f"{rr:.1f}:1" if rr > 0 else "-",
            )

        # Max profit (resolution at 1.0 or 0.0)
        table.add_row(
            "[bright_green]Max Profit[/bright_green]",
            f"{strategy['max_profit_price']:.2f}",
            f"[bright_green]+${strategy['max_profit']:,.2f}[/bright_green]",
            f"[bright_green]+{strategy['max_profit_roi']:.1%}[/bright_green]",
            "-",
        )

        console.print(table)
        console.print()

        # Risk metrics
        console.print("[bold]Risk Metrics:[/bold]")
        console.print(f"  Max Loss: [red]${strategy['max_loss']:,.2f}[/red] (if resolves {strategy['loss_resolution']})")
        console.print(f"  Max Profit: [green]${strategy['max_profit']:,.2f}[/green] (if resolves {strategy['profit_resolution']})")
        console.print(f"  Risk/Reward: {strategy['risk_reward']:.2f}:1")
        console.print()

        # Save option
        if interactive:
            if Confirm.ask("[cyan]Save this exit plan?[/cyan]", default=False):
                plan_id = _save_exit_plan(db, market_id, title, entry, shares, side, strategy)
                console.print(f"[green]Exit plan saved (ID: {plan_id})[/green]")
                console.print("[dim]Use 'polyterm pricealert' to set alerts at these levels[/dim]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _get_price(market: dict) -> float:
    """Get current market price"""
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


def _calculate_exit_strategy(entry: float, shares: float, side: str, current_price: float) -> dict:
    """Calculate exit strategy with targets and stops"""
    cost_basis = entry * shares

    # For YES positions: profit when price goes up
    # For NO positions: profit when price goes down (you bought NO at entry price)

    if side == "yes":
        # Breakeven is entry price (ignoring fees for simplicity)
        breakeven = entry

        # Current P&L
        current_value = current_price * shares
        current_pnl = current_value - cost_basis

        # Max profit: price goes to 1.0
        max_profit = (1.0 - entry) * shares
        max_profit_price = 1.0
        max_profit_roi = max_profit / cost_basis if cost_basis > 0 else 0

        # Max loss: price goes to 0.0
        max_loss = cost_basis
        loss_resolution = "NO"
        profit_resolution = "YES"

        # Stop loss levels
        stop_losses = []
        for pct in [0.1, 0.25, 0.5]:  # 10%, 25%, 50% loss
            sl_price = entry * (1 - pct)
            if sl_price >= 0:
                sl_pnl = (sl_price - entry) * shares
                stop_losses.append({
                    'label': f"Stop {pct:.0%}",
                    'price': sl_price,
                    'pnl': sl_pnl,
                    'roi': sl_pnl / cost_basis if cost_basis > 0 else 0,
                })

        # Take profit levels
        take_profits = []
        for pct in [0.25, 0.5, 1.0, 2.0]:  # 25%, 50%, 100%, 200% profit
            tp_price = entry * (1 + pct)
            if tp_price <= 1.0:
                tp_pnl = (tp_price - entry) * shares
                take_profits.append({
                    'label': f"TP +{pct:.0%}",
                    'price': tp_price,
                    'pnl': tp_pnl,
                    'roi': tp_pnl / cost_basis if cost_basis > 0 else 0,
                })

    else:  # NO position
        # For NO: you paid (1 - entry) effectively, profit when price drops
        no_cost = (1 - entry) * shares
        breakeven = entry

        # Current P&L (NO profits when YES price drops)
        current_pnl = (entry - current_price) * shares

        # Max profit: YES price goes to 0.0
        max_profit = entry * shares
        max_profit_price = 0.0
        max_profit_roi = max_profit / no_cost if no_cost > 0 else 0

        # Max loss: YES price goes to 1.0
        max_loss = (1 - entry) * shares
        loss_resolution = "YES"
        profit_resolution = "NO"

        # Stop loss levels (price goes UP for NO holder)
        stop_losses = []
        for pct in [0.1, 0.25, 0.5]:
            sl_price = entry + (1 - entry) * pct
            if sl_price <= 1.0:
                sl_pnl = (entry - sl_price) * shares
                stop_losses.append({
                    'label': f"Stop {pct:.0%}",
                    'price': sl_price,
                    'pnl': sl_pnl,
                    'roi': sl_pnl / no_cost if no_cost > 0 else 0,
                })

        # Take profit levels (price goes DOWN for NO holder)
        take_profits = []
        for pct in [0.25, 0.5, 1.0, 2.0]:
            tp_price = entry * (1 - pct * 0.5)  # Scale down
            if tp_price >= 0:
                tp_pnl = (entry - tp_price) * shares
                if tp_pnl > 0:
                    take_profits.append({
                        'label': f"TP +{pct:.0%}",
                        'price': tp_price,
                        'pnl': tp_pnl,
                        'roi': tp_pnl / no_cost if no_cost > 0 else 0,
                    })

        cost_basis = no_cost

    current_pnl_pct = current_pnl / cost_basis if cost_basis > 0 else 0
    risk_reward = max_profit / max_loss if max_loss > 0 else float('inf')

    return {
        'cost_basis': entry * shares if side == 'yes' else (1 - entry) * shares,
        'breakeven': breakeven,
        'current_pnl': current_pnl,
        'current_pnl_pct': current_pnl_pct,
        'stop_losses': stop_losses,
        'take_profits': take_profits,
        'max_profit': max_profit,
        'max_profit_price': max_profit_price,
        'max_profit_roi': max_profit_roi,
        'max_loss': max_loss,
        'loss_resolution': loss_resolution,
        'profit_resolution': profit_resolution,
        'risk_reward': risk_reward,
    }


def _save_exit_plan(db: Database, market_id: str, title: str, entry: float, shares: float, side: str, strategy: dict) -> int:
    """Save exit plan to database"""
    import json

    with db._get_connection() as conn:
        cursor = conn.cursor()

        # Create table if not exists
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS exit_plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                market_id TEXT NOT NULL,
                title TEXT NOT NULL,
                entry_price REAL NOT NULL,
                shares REAL NOT NULL,
                side TEXT NOT NULL,
                strategy TEXT NOT NULL,
                created_at TIMESTAMP NOT NULL
            )
        """)

        cursor.execute("""
            INSERT INTO exit_plans (market_id, title, entry_price, shares, side, strategy, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (market_id, title, entry, shares, side, json.dumps(strategy), datetime.now().isoformat()))

        return cursor.lastrowid


def _list_exit_plans(console: Console, db: Database, output_format: str):
    """List saved exit plans"""
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM exit_plans ORDER BY created_at DESC
            """)
            plans = [dict(row) for row in cursor.fetchall()]
    except Exception:
        plans = []

    if output_format == 'json':
        print_json({'success': True, 'plans': plans})
        return

    if not plans:
        console.print("[yellow]No exit plans saved.[/yellow]")
        console.print("[dim]Use 'polyterm exit --interactive' to create one.[/dim]")
        return

    console.print()
    console.print(Panel("[bold]Saved Exit Plans[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", width=4)
    table.add_column("Market", max_width=40)
    table.add_column("Side", width=5)
    table.add_column("Entry", width=8)
    table.add_column("Shares", width=10)
    table.add_column("Created")

    for plan in plans:
        table.add_row(
            str(plan['id']),
            plan['title'][:38],
            plan['side'].upper(),
            f"{plan['entry_price']:.2f}",
            f"{plan['shares']:,.0f}",
            plan['created_at'][:10],
        )

    console.print(table)
    console.print()


def _delete_exit_plan(console: Console, db: Database, plan_id: int, output_format: str):
    """Delete an exit plan"""
    try:
        with db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM exit_plans WHERE id = ?", (plan_id,))
            deleted = cursor.rowcount > 0

        if output_format == 'json':
            print_json({'success': deleted, 'deleted_id': plan_id if deleted else None})
        else:
            if deleted:
                console.print(f"[green]Exit plan {plan_id} deleted.[/green]")
            else:
                console.print(f"[yellow]Exit plan {plan_id} not found.[/yellow]")
    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
