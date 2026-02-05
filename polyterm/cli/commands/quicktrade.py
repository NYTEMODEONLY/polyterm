"""Quick Trade - Prepare trades and get direct Polymarket links"""

import click
import webbrowser
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


def search_markets_fallback(gamma_client: GammaClient, query: str, limit: int = 5) -> list:
    """Search markets with fallback to filtering get_markets results"""
    # Try search endpoint first
    try:
        results = gamma_client.search_markets(query, limit=limit)
        if results:
            return results
    except Exception:
        pass

    # Fallback: get all markets and filter locally
    try:
        markets = gamma_client.get_markets(limit=200)
        query_lower = query.lower()

        matches = []
        for market in markets:
            title = market.get('question', market.get('title', '')).lower()
            if query_lower in title:
                matches.append(market)
                if len(matches) >= limit:
                    break

        return matches
    except Exception:
        return []


def get_market_price(market: dict) -> tuple:
    """Extract YES/NO prices from market"""
    outcome_prices = market.get('outcomePrices')
    if not outcome_prices and market.get('markets') and len(market.get('markets', [])) > 0:
        outcome_prices = market['markets'][0].get('outcomePrices')

    if isinstance(outcome_prices, str):
        import json
        try:
            outcome_prices = json.loads(outcome_prices)
        except Exception:
            return 0.5, 0.5

    if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) >= 2:
        return float(outcome_prices[0]), float(outcome_prices[1])
    elif outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) == 1:
        yes = float(outcome_prices[0])
        return yes, 1 - yes

    return 0.5, 0.5


def calculate_trade(amount: float, price: float, side: str) -> dict:
    """Calculate trade details"""
    shares = amount / price if price > 0 else 0

    # Polymarket fee: 2% on winnings (taker)
    win_payout = shares * 1.0  # $1 per share if wins
    gross_profit = win_payout - amount
    fee_on_profit = max(0, gross_profit) * 0.02
    net_profit = gross_profit - fee_on_profit

    loss = -amount  # Lose entire stake if wrong

    roi = (net_profit / amount) * 100 if amount > 0 else 0
    breakeven = price / (0.98 + 0.02 * price)  # Exact breakeven accounting for 2% fee on winnings

    # Expected value (assuming market price = fair probability)
    prob = price
    ev = (prob * net_profit) + ((1 - prob) * loss)

    return {
        'amount': amount,
        'price': price,
        'side': side,
        'shares': shares,
        'win_payout': win_payout,
        'gross_profit': gross_profit,
        'fee': fee_on_profit,
        'net_profit': net_profit,
        'loss': loss,
        'roi': roi,
        'breakeven': breakeven,
        'ev': ev,
    }


@click.command()
@click.option("--market", "-m", "search_term", default=None, help="Market to trade")
@click.option("--amount", "-a", type=float, default=100, help="Trade amount ($)")
@click.option("--side", "-s", type=click.Choice(["yes", "no"]), default=None, help="Side to buy")
@click.option("--open-browser", "-o", is_flag=True, help="Open Polymarket in browser")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def quicktrade(ctx, search_term, amount, side, open_browser, interactive, output_format):
    """Prepare a trade and get direct Polymarket link

    Analyzes your trade parameters and provides a direct link to execute
    on Polymarket. This tool does NOT execute trades - it prepares the
    analysis and opens the market page for you.

    Examples:
        polyterm quicktrade -m "bitcoin" -a 200 -s yes     # Prepare $200 YES on BTC
        polyterm quicktrade -m "trump" -a 50 -s no -o      # Prepare + open browser
        polyterm quicktrade -i                              # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )

    try:
        # Interactive mode
        if interactive:
            console.print()
            console.print(Panel(
                "[bold cyan]Quick Trade Preparation[/bold cyan]\n\n"
                "Analyze and prepare trades for Polymarket.\n"
                "[dim]Generates analysis + direct link to execute.[/dim]",
                border_style="cyan"
            ))
            console.print()

            search_term = Prompt.ask("[cyan]Search for market[/cyan]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Searching...", total=None)
                markets = search_markets_fallback(gamma_client, search_term, limit=5)

            if not markets:
                console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
                return

            # Display found markets
            console.print()
            console.print("[bold]Found Markets:[/bold]")
            for i, m in enumerate(markets, 1):
                title = m.get('question', m.get('title', ''))[:50]
                yes_price, no_price = get_market_price(m)
                console.print(f"  [{i}] {title}")
                console.print(f"      [green]YES: {yes_price:.0%}[/green] | [red]NO: {no_price:.0%}[/red]")
            console.print()

            idx_str = Prompt.ask("Select market number", default="1")
            try:
                idx = int(idx_str) - 1
                if idx < 0 or idx >= len(markets):
                    console.print("[yellow]Invalid selection[/yellow]")
                    return
                market = markets[idx]
            except ValueError:
                console.print("[yellow]Invalid selection[/yellow]")
                return

            # Get trade parameters
            side = Prompt.ask("[cyan]Side[/cyan]", choices=["yes", "no"], default="yes")
            amount_str = Prompt.ask("[cyan]Amount ($)[/cyan]", default="100")
            try:
                amount = float(amount_str)
            except ValueError:
                amount = 100

        else:
            # Non-interactive mode
            if not search_term:
                console.print("[yellow]Please specify a market with -m or use --interactive[/yellow]")
                return

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True,
            ) as progress:
                progress.add_task("Searching...", total=None)
                markets = search_markets_fallback(gamma_client, search_term, limit=1)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
                else:
                    console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
                return

            market = markets[0]

            if not side:
                # Default to YES
                side = "yes"

        # Extract market info
        market_id = market.get('id', market.get('condition_id', ''))
        market_slug = market.get('slug', '')
        title = market.get('question', market.get('title', ''))
        yes_price, no_price = get_market_price(market)
        volume = float(market.get('volume24hr', market.get('volume', 0)) or 0)
        liquidity = float(market.get('liquidity', 0) or 0)

        # Calculate trade
        price = yes_price if side == "yes" else no_price
        trade = calculate_trade(amount, price, side)

        # Generate Polymarket URL
        # Format: https://polymarket.com/event/{slug} or /event/{id}
        if market_slug:
            trade_url = f"https://polymarket.com/event/{market_slug}"
        elif market_id:
            trade_url = f"https://polymarket.com/event/{market_id}"
        else:
            trade_url = "https://polymarket.com"

        # JSON output
        if output_format == 'json':
            print_json({
                'success': True,
                'market': {
                    'id': market_id,
                    'slug': market_slug,
                    'title': title,
                    'yes_price': yes_price,
                    'no_price': no_price,
                    'volume': volume,
                    'liquidity': liquidity,
                },
                'trade': trade,
                'url': trade_url,
            })
            return

        # Display trade preparation
        console.print()
        console.print(Panel(f"[bold]{title[:60]}[/bold]", border_style="cyan"))
        console.print()

        # Market info
        console.print("[bold]Market Info:[/bold]")
        info_table = Table(show_header=False, box=None)
        info_table.add_column(width=20)
        info_table.add_column(width=15, justify="right")

        info_table.add_row("YES Price", f"[green]{yes_price:.2f}[/green] ({yes_price:.0%})")
        info_table.add_row("NO Price", f"[red]{no_price:.2f}[/red] ({no_price:.0%})")
        info_table.add_row("24h Volume", f"${volume:,.0f}")
        info_table.add_row("Liquidity", f"${liquidity:,.0f}")

        console.print(info_table)
        console.print()

        # Trade details
        side_color = "green" if side == "yes" else "red"
        console.print(Panel(
            f"[bold {side_color}]BUY {side.upper()}[/bold {side_color}] - ${amount:,.2f}",
            border_style=side_color,
        ))
        console.print()

        trade_table = Table(show_header=False, box=None)
        trade_table.add_column(width=20)
        trade_table.add_column(width=15, justify="right")

        trade_table.add_row("Entry Price", f"${trade['price']:.3f}")
        trade_table.add_row("Shares", f"{trade['shares']:,.1f}")
        trade_table.add_row("", "")
        trade_table.add_row("[bold]If You Win:[/bold]", "")
        trade_table.add_row("  Payout", f"${trade['win_payout']:,.2f}")
        trade_table.add_row("  Profit (gross)", f"[green]+${trade['gross_profit']:,.2f}[/green]")
        trade_table.add_row("  Fee (2%)", f"[yellow]-${trade['fee']:,.2f}[/yellow]")
        trade_table.add_row("  Profit (net)", f"[green]+${trade['net_profit']:,.2f}[/green]")
        trade_table.add_row("  ROI", f"[green]+{trade['roi']:.1f}%[/green]")
        trade_table.add_row("", "")
        trade_table.add_row("[bold]If You Lose:[/bold]", "")
        trade_table.add_row("  Loss", f"[red]-${amount:,.2f}[/red]")
        trade_table.add_row("", "")
        trade_table.add_row("Breakeven", f"{trade['breakeven']:.1%}")
        ev_color = "green" if trade['ev'] >= 0 else "red"
        trade_table.add_row("Expected Value*", f"[{ev_color}]${trade['ev']:+,.2f}[/{ev_color}]")

        console.print(trade_table)
        console.print()
        console.print("[dim]*EV assumes market price equals true probability[/dim]")
        console.print()

        # Trade URL
        console.print(Panel(
            f"[bold]Trade on Polymarket:[/bold]\n{trade_url}",
            border_style="cyan",
        ))
        console.print()

        # Open browser if requested
        if open_browser:
            console.print("[dim]Opening Polymarket...[/dim]")
            webbrowser.open(trade_url)
        elif interactive:
            if Confirm.ask("Open in browser?", default=False):
                webbrowser.open(trade_url)

        # Quick tips
        console.print("[bold]Before Trading:[/bold]")
        console.print("  1. Review order book depth for large trades")
        console.print("  2. Consider limit orders to reduce slippage")
        console.print("  3. Check market resolution criteria")
        console.print()

    finally:
        gamma_client.close()
        clob_client.close()
