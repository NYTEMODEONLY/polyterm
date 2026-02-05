"""Quick Actions Command - Fast access to common workflows"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.argument("action", required=False, type=click.Choice(["price", "buy", "sell", "info", "watch"]))
@click.argument("market", required=False)
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def quick(ctx, action, market, output_format):
    """Quick actions for common trading tasks

    One-liner commands for fast market checks and calculations.
    Perfect for power users who want speed.

    Actions:
        price  - Quick price check
        buy    - Quick buy calculation
        sell   - Quick sell calculation
        info   - Quick market info
        watch  - Add to watchlist

    Examples:
        polyterm quick price bitcoin       # Check price
        polyterm quick buy "trump wins"    # Calculate buy
        polyterm quick info election       # Market info
        polyterm quick                     # Interactive menu
    """
    console = Console()
    config = ctx.obj["config"]

    if not action:
        # Interactive menu
        console.print()
        console.print(Panel("[bold]Quick Actions[/bold]", border_style="cyan"))
        console.print()
        console.print("[cyan]Available actions:[/cyan]")
        console.print("  [yellow]1.[/yellow] price - Check market price")
        console.print("  [yellow]2.[/yellow] buy   - Calculate buy order")
        console.print("  [yellow]3.[/yellow] sell  - Calculate sell order")
        console.print("  [yellow]4.[/yellow] info  - Full market info")
        console.print("  [yellow]5.[/yellow] watch - Add to watchlist")
        console.print()

        choice = Prompt.ask("[cyan]Select action[/cyan]", choices=["1", "2", "3", "4", "5", "price", "buy", "sell", "info", "watch"])

        action_map = {"1": "price", "2": "buy", "3": "sell", "4": "info", "5": "watch"}
        action = action_map.get(choice, choice)

        console.print()
        market = Prompt.ask("[cyan]Market[/cyan]")

        if not market:
            return

        console.print()

    if not market:
        console.print("[yellow]Please specify a market[/yellow]")
        return

    gamma = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Find market
        markets = gamma.search_markets(market, limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': f'Market not found: {market}'})
            else:
                console.print(f"[yellow]Market not found: {market}[/yellow]")
            return

        m = markets[0]
        title = m.get('question', m.get('title', ''))
        market_id = m.get('id', m.get('condition_id', ''))

        # Get price
        yes_price = 0.5
        no_price = 0.5
        for token in m.get('tokens', []):
            if token.get('outcome', '').upper() == 'YES':
                try:
                    yes_price = float(token.get('price', 0.5))
                    no_price = 1 - yes_price
                except Exception:
                    pass
                break

        volume_24h = float(m.get('volume24hr', 0) or 0)
        liquidity = float(m.get('liquidity', 0) or 0)

        if action == "price":
            _quick_price(console, title, yes_price, no_price, volume_24h, output_format)

        elif action == "buy":
            _quick_buy(console, title, yes_price, no_price, output_format)

        elif action == "sell":
            _quick_sell(console, title, yes_price, no_price, output_format)

        elif action == "info":
            _quick_info(console, m, yes_price, volume_24h, liquidity, output_format)

        elif action == "watch":
            _quick_watch(console, title, market_id, yes_price)

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma.close()


def _quick_price(console: Console, title: str, yes_price: float, no_price: float, volume: float, output_format: str):
    """Quick price check"""
    if output_format == 'json':
        print_json({
            'market': title,
            'yes_price': yes_price,
            'no_price': no_price,
            'volume_24h': volume,
        })
        return

    # One-liner output
    console.print()
    console.print(f"[bold]{title[:60]}[/bold]")
    console.print()
    console.print(f"  [green]YES[/green] {yes_price:.0%}  |  [red]NO[/red] {no_price:.0%}  |  Vol: ${volume:,.0f}")
    console.print()


def _quick_buy(console: Console, title: str, yes_price: float, no_price: float, output_format: str):
    """Quick buy calculation"""
    console.print()
    console.print(f"[bold]{title[:50]}[/bold]")
    console.print()

    # Get side
    side = Prompt.ask("[cyan]Side[/cyan]", choices=["YES", "NO", "yes", "no"], default="YES")
    side = side.upper()

    price = yes_price if side == "YES" else no_price

    # Get amount
    amount_str = Prompt.ask("[cyan]Amount ($)[/cyan]", default="100")
    try:
        amount = float(amount_str)
    except ValueError:
        amount = 100

    # Calculate
    shares = amount / price if price > 0 else 0
    potential_profit = shares - amount  # If wins, get $1 per share

    if output_format == 'json':
        print_json({
            'side': side,
            'price': price,
            'amount': amount,
            'shares': shares,
            'potential_profit': potential_profit,
        })
        return

    console.print()
    console.print(f"[bold]Quick Buy: {side}[/bold]")
    console.print()
    console.print(f"  Price: {price:.2%}")
    console.print(f"  Cost: ${amount:,.2f}")
    console.print(f"  Shares: {shares:,.2f}")
    console.print(f"  If {side} wins: [green]+${potential_profit:,.2f}[/green]")
    console.print(f"  If {side} loses: [red]-${amount:,.2f}[/red]")
    console.print()


def _quick_sell(console: Console, title: str, yes_price: float, no_price: float, output_format: str):
    """Quick sell calculation"""
    console.print()
    console.print(f"[bold]{title[:50]}[/bold]")
    console.print()

    # Get side
    side = Prompt.ask("[cyan]Side to sell[/cyan]", choices=["YES", "NO", "yes", "no"], default="YES")
    side = side.upper()

    price = yes_price if side == "YES" else no_price

    # Get shares
    shares_str = Prompt.ask("[cyan]Shares to sell[/cyan]", default="100")
    try:
        shares = float(shares_str)
    except ValueError:
        shares = 100

    # Get entry price
    entry_str = Prompt.ask("[cyan]Entry price (e.g., 0.40)[/cyan]", default=str(price))
    try:
        entry_price = float(entry_str)
    except ValueError:
        entry_price = price

    # Calculate
    proceeds = shares * price
    cost_basis = shares * entry_price
    pnl = proceeds - cost_basis
    pnl_pct = (pnl / cost_basis * 100) if cost_basis > 0 else 0

    if output_format == 'json':
        print_json({
            'side': side,
            'shares': shares,
            'current_price': price,
            'entry_price': entry_price,
            'proceeds': proceeds,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
        })
        return

    pnl_color = "green" if pnl >= 0 else "red"

    console.print()
    console.print(f"[bold]Quick Sell: {side}[/bold]")
    console.print()
    console.print(f"  Current Price: {price:.2%}")
    console.print(f"  Shares: {shares:,.2f}")
    console.print(f"  Proceeds: ${proceeds:,.2f}")
    console.print(f"  Entry: {entry_price:.2%} (${cost_basis:,.2f})")
    console.print(f"  P&L: [{pnl_color}]${pnl:+,.2f} ({pnl_pct:+.1f}%)[/{pnl_color}]")
    console.print()


def _quick_info(console: Console, market: dict, price: float, volume: float, liquidity: float, output_format: str):
    """Quick market info"""
    title = market.get('question', market.get('title', ''))
    description = market.get('description', '')[:200]
    category = market.get('category', 'Unknown')
    end_date = market.get('endDate', 'N/A')
    total_volume = float(market.get('volume', 0) or 0)

    if output_format == 'json':
        print_json({
            'title': title,
            'category': category,
            'price': price,
            'volume_24h': volume,
            'total_volume': total_volume,
            'liquidity': liquidity,
            'end_date': end_date,
            'description': description,
        })
        return

    console.print()
    console.print(Panel(f"[bold]{title}[/bold]", border_style="cyan"))
    console.print()

    info = Table(show_header=False, box=None)
    info.add_column(style="cyan", width=15)
    info.add_column(width=40)

    info.add_row("Category:", category)
    info.add_row("Price:", f"{price:.0%}")
    info.add_row("24h Volume:", f"${volume:,.0f}")
    info.add_row("Total Volume:", f"${total_volume:,.0f}")
    info.add_row("Liquidity:", f"${liquidity:,.0f}")
    info.add_row("End Date:", end_date[:10] if end_date != 'N/A' else 'N/A')

    console.print(info)

    if description:
        console.print()
        console.print("[dim]" + description + "[/dim]")

    console.print()


def _quick_watch(console: Console, title: str, market_id: str, price: float):
    """Quick add to bookmarks (watchlist)"""
    from ...db.database import Database

    db = Database()

    # Check if already bookmarked
    bookmarks = db.get_bookmarks()
    existing = any(b.get('market_id') == market_id for b in bookmarks)

    if existing:
        console.print()
        console.print(f"[yellow]Already bookmarked: {title[:50]}[/yellow]")
        console.print()
        return

    # Add to bookmarks
    db.bookmark_market(market_id, title, '', price, 'Added via quick update')

    console.print()
    console.print(f"[green]Bookmarked: {title[:50]}[/green]")
    console.print(f"[dim]Current price: {price:.0%}[/dim]")
    console.print()
