"""Report Command - Generate comprehensive market reports"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from datetime import datetime
from pathlib import Path

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--type", "-t", "report_type", type=click.Choice(["daily", "weekly", "portfolio", "market"]),
              default="daily", help="Type of report")
@click.option("--market", "-m", default=None, help="Specific market for market report")
@click.option("--output", "-o", default=None, help="Output file path (optional)")
@click.option("--format", "output_format", type=click.Choice(["table", "json", "markdown"]), default="table")
@click.pass_context
def report(ctx, report_type, market, output, output_format):
    """Generate comprehensive trading reports

    Create detailed reports for analysis and record-keeping.
    Reports can be exported to JSON or Markdown format.

    Report Types:
        daily     - Daily market summary
        weekly    - Weekly performance review
        portfolio - Your positions and P&L
        market    - Deep dive on a specific market

    Examples:
        polyterm report -t daily               # Daily summary
        polyterm report -t portfolio           # Portfolio report
        polyterm report -t market -m "bitcoin" # Market analysis
        polyterm report -t weekly -o report.md --format markdown
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Generating report...", total=None)

            if report_type == "daily":
                report_data = _generate_daily_report(gamma_client)
            elif report_type == "weekly":
                report_data = _generate_weekly_report(gamma_client)
            elif report_type == "portfolio":
                report_data = _generate_portfolio_report(gamma_client, config)
            elif report_type == "market":
                if not market:
                    if output_format == 'json':
                        print_json({'success': False, 'error': 'Market required for market report'})
                    else:
                        console.print("[yellow]Please specify a market with -m[/yellow]")
                    return
                report_data = _generate_market_report(gamma_client, market)
            else:
                report_data = {}

        # Handle output
        if output_format == "json":
            if output:
                with open(output, 'w') as f:
                    import json
                    json.dump(report_data, f, indent=2, default=str)
                console.print(f"[green]Report saved to {output}[/green]")
            else:
                print_json(report_data)
            return

        if output_format == "markdown":
            md_content = _to_markdown(report_data, report_type)
            if output:
                with open(output, 'w') as f:
                    f.write(md_content)
                console.print(f"[green]Report saved to {output}[/green]")
            else:
                console.print(md_content)
            return

        # Display in terminal
        _display_report(console, report_data, report_type)

        if output:
            # Also save table output
            with open(output, 'w') as f:
                f.write(_to_markdown(report_data, report_type))
            console.print(f"\n[green]Report also saved to {output}[/green]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()


def _generate_daily_report(gamma: GammaClient) -> dict:
    """Generate daily market report"""
    markets = gamma.get_markets(limit=100)

    # Top movers
    movers = []
    for m in markets:
        price = 0.5
        tokens = m.get('tokens', [])
        for t in tokens:
            if t.get('outcome', '').upper() == 'YES':
                try:
                    price = float(t.get('price', 0.5))
                except:
                    pass
                break

        prev = float(m.get('previousYesPrice', price) or price)
        change = ((price - prev) / prev * 100) if prev > 0 else 0

        movers.append({
            'title': m.get('question', m.get('title', ''))[:50],
            'price': price,
            'change': change,
            'volume': float(m.get('volume24hr', 0) or 0),
        })

    movers.sort(key=lambda x: abs(x['change']), reverse=True)

    # Volume leaders
    by_volume = sorted(movers, key=lambda x: x['volume'], reverse=True)

    # Stats
    total_volume = sum(m['volume'] for m in movers)
    avg_change = sum(abs(m['change']) for m in movers) / len(movers) if movers else 0
    gainers = len([m for m in movers if m['change'] > 0])
    losers = len([m for m in movers if m['change'] < 0])

    return {
        'type': 'daily',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'summary': {
            'total_markets': len(movers),
            'total_volume_24h': total_volume,
            'avg_change': avg_change,
            'gainers': gainers,
            'losers': losers,
        },
        'top_movers': movers[:10],
        'volume_leaders': by_volume[:10],
    }


def _generate_weekly_report(gamma: GammaClient) -> dict:
    """Generate weekly report"""
    markets = gamma.get_markets(limit=100)

    # Aggregate data
    total_volume = sum(float(m.get('volume', 0) or 0) for m in markets)
    categories = {}

    for m in markets:
        cat = m.get('category', 'Other') or 'Other'
        if cat not in categories:
            categories[cat] = {'count': 0, 'volume': 0}
        categories[cat]['count'] += 1
        categories[cat]['volume'] += float(m.get('volume24hr', 0) or 0)

    # Sort categories by volume
    cat_list = [{'name': k, **v} for k, v in categories.items()]
    cat_list.sort(key=lambda x: x['volume'], reverse=True)

    return {
        'type': 'weekly',
        'week_of': datetime.now().strftime('%Y-%m-%d'),
        'summary': {
            'total_markets': len(markets),
            'total_volume': total_volume,
            'categories': len(categories),
        },
        'by_category': cat_list[:10],
        'highlights': [
            m.get('question', m.get('title', ''))[:50]
            for m in sorted(markets, key=lambda x: float(x.get('volume24hr', 0) or 0), reverse=True)[:5]
        ],
    }


def _generate_portfolio_report(gamma: GammaClient, config) -> dict:
    """Generate portfolio report"""
    db = Database()

    # Get positions
    positions = db.get_all_positions()

    total_invested = 0
    total_value = 0
    position_data = []

    markets = gamma.get_markets(limit=200)
    market_prices = {}

    for m in markets:
        title = m.get('question', m.get('title', ''))
        price = 0.5
        for t in m.get('tokens', []):
            if t.get('outcome', '').upper() == 'YES':
                try:
                    price = float(t.get('price', 0.5))
                except:
                    pass
                break
        market_prices[title.lower()[:30]] = price

    for pos in positions:
        market_key = pos.get('market_name', '')[:30].lower()
        current_price = market_prices.get(market_key, pos.get('current_price', pos.get('entry_price', 0.5)))

        entry = float(pos.get('entry_price', 0.5))
        shares = float(pos.get('shares', 0))
        side = pos.get('side', 'YES')

        invested = entry * shares
        current_value = current_price * shares if side == 'YES' else (1 - current_price) * shares

        pnl = current_value - invested
        pnl_pct = (pnl / invested * 100) if invested > 0 else 0

        total_invested += invested
        total_value += current_value

        position_data.append({
            'market': pos.get('market_name', 'Unknown')[:40],
            'side': side,
            'shares': shares,
            'entry': entry,
            'current': current_price,
            'value': current_value,
            'pnl': pnl,
            'pnl_pct': pnl_pct,
        })

    total_pnl = total_value - total_invested
    total_pnl_pct = (total_pnl / total_invested * 100) if total_invested > 0 else 0

    return {
        'type': 'portfolio',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'summary': {
            'total_positions': len(position_data),
            'total_invested': total_invested,
            'total_value': total_value,
            'total_pnl': total_pnl,
            'total_pnl_pct': total_pnl_pct,
        },
        'positions': position_data,
    }


def _generate_market_report(gamma: GammaClient, search: str) -> dict:
    """Generate detailed market report"""
    markets = gamma.search_markets(search, limit=1)

    if not markets:
        return {'error': f'Market not found: {search}'}

    m = markets[0]

    price = 0.5
    for t in m.get('tokens', []):
        if t.get('outcome', '').upper() == 'YES':
            try:
                price = float(t.get('price', 0.5))
            except:
                pass
            break

    prev = float(m.get('previousYesPrice', price) or price)
    change = ((price - prev) / prev * 100) if prev > 0 else 0

    return {
        'type': 'market',
        'date': datetime.now().strftime('%Y-%m-%d'),
        'market': {
            'id': m.get('id', m.get('condition_id', '')),
            'title': m.get('question', m.get('title', '')),
            'description': m.get('description', '')[:500],
            'category': m.get('category', 'Unknown'),
        },
        'pricing': {
            'current_price': price,
            'implied_probability': f"{price:.1%}",
            'change_24h': change,
            'volume_24h': float(m.get('volume24hr', 0) or 0),
            'total_volume': float(m.get('volume', 0) or 0),
            'liquidity': float(m.get('liquidity', 0) or 0),
        },
        'dates': {
            'end_date': m.get('endDate', 'N/A'),
            'created': m.get('createdAt', 'N/A'),
        },
    }


def _display_report(console: Console, data: dict, report_type: str):
    """Display report in terminal"""
    console.print()
    console.print(Panel(f"[bold]{report_type.title()} Report - {data.get('date', data.get('week_of', ''))}[/bold]",
                       border_style="cyan"))
    console.print()

    if report_type == "daily":
        summary = data.get('summary', {})
        console.print("[bold]Summary:[/bold]")
        console.print(f"  Markets Tracked: {summary.get('total_markets', 0)}")
        console.print(f"  24h Volume: ${summary.get('total_volume_24h', 0):,.0f}")
        console.print(f"  Avg Movement: {summary.get('avg_change', 0):.1f}%")
        console.print(f"  Gainers/Losers: [green]{summary.get('gainers', 0)}[/green] / [red]{summary.get('losers', 0)}[/red]")
        console.print()

        console.print("[bold]Top Movers:[/bold]")
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("Market", width=40)
        table.add_column("Price", width=8, justify="center")
        table.add_column("Change", width=10, justify="center")

        for m in data.get('top_movers', [])[:5]:
            color = "green" if m['change'] > 0 else "red"
            table.add_row(m['title'], f"{m['price']:.0%}", f"[{color}]{m['change']:+.1f}%[/{color}]")

        console.print(table)
        console.print()

    elif report_type == "weekly":
        summary = data.get('summary', {})
        console.print("[bold]Weekly Summary:[/bold]")
        console.print(f"  Total Markets: {summary.get('total_markets', 0)}")
        console.print(f"  Total Volume: ${summary.get('total_volume', 0):,.0f}")
        console.print()

        console.print("[bold]Top Categories:[/bold]")
        for cat in data.get('by_category', [])[:5]:
            console.print(f"  {cat['name']}: {cat['count']} markets, ${cat['volume']:,.0f} volume")
        console.print()

    elif report_type == "portfolio":
        summary = data.get('summary', {})
        pnl_color = "green" if summary.get('total_pnl', 0) > 0 else "red"

        console.print("[bold]Portfolio Summary:[/bold]")
        console.print(f"  Positions: {summary.get('total_positions', 0)}")
        console.print(f"  Invested: ${summary.get('total_invested', 0):,.2f}")
        console.print(f"  Current Value: ${summary.get('total_value', 0):,.2f}")
        console.print(f"  P&L: [{pnl_color}]${summary.get('total_pnl', 0):+,.2f} ({summary.get('total_pnl_pct', 0):+.1f}%)[/{pnl_color}]")
        console.print()

        if data.get('positions'):
            console.print("[bold]Positions:[/bold]")
            table = Table(show_header=True, header_style="bold cyan", box=None)
            table.add_column("Market", width=35)
            table.add_column("Side", width=6)
            table.add_column("Entry", width=8)
            table.add_column("Current", width=8)
            table.add_column("P&L", width=15)

            for p in data['positions']:
                color = "green" if p['pnl'] > 0 else "red"
                table.add_row(
                    p['market'],
                    p['side'],
                    f"{p['entry']:.0%}",
                    f"{p['current']:.0%}",
                    f"[{color}]${p['pnl']:+,.2f} ({p['pnl_pct']:+.1f}%)[/{color}]",
                )

            console.print(table)
        console.print()

    elif report_type == "market":
        if 'error' in data:
            console.print(f"[red]{data['error']}[/red]")
            return

        market_info = data.get('market', {})
        pricing = data.get('pricing', {})

        console.print(f"[bold]{market_info.get('title', 'Unknown')}[/bold]")
        console.print(f"[dim]Category: {market_info.get('category', 'Unknown')}[/dim]")
        console.print()

        console.print("[bold]Pricing:[/bold]")
        change_color = "green" if pricing.get('change_24h', 0) > 0 else "red"
        console.print(f"  Current Price: {pricing.get('current_price', 0):.2%}")
        console.print(f"  24h Change: [{change_color}]{pricing.get('change_24h', 0):+.1f}%[/{change_color}]")
        console.print(f"  24h Volume: ${pricing.get('volume_24h', 0):,.0f}")
        console.print(f"  Total Volume: ${pricing.get('total_volume', 0):,.0f}")
        console.print(f"  Liquidity: ${pricing.get('liquidity', 0):,.0f}")
        console.print()


def _to_markdown(data: dict, report_type: str) -> str:
    """Convert report to markdown"""
    lines = []
    lines.append(f"# {report_type.title()} Report")
    lines.append(f"*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append("")

    if report_type == "daily":
        summary = data.get('summary', {})
        lines.append("## Summary")
        lines.append(f"- Markets Tracked: {summary.get('total_markets', 0)}")
        lines.append(f"- 24h Volume: ${summary.get('total_volume_24h', 0):,.0f}")
        lines.append(f"- Gainers: {summary.get('gainers', 0)}")
        lines.append(f"- Losers: {summary.get('losers', 0)}")
        lines.append("")

        lines.append("## Top Movers")
        lines.append("| Market | Price | Change |")
        lines.append("|--------|-------|--------|")
        for m in data.get('top_movers', [])[:10]:
            lines.append(f"| {m['title']} | {m['price']:.0%} | {m['change']:+.1f}% |")
        lines.append("")

    elif report_type == "portfolio":
        summary = data.get('summary', {})
        lines.append("## Portfolio Summary")
        lines.append(f"- Total Positions: {summary.get('total_positions', 0)}")
        lines.append(f"- Invested: ${summary.get('total_invested', 0):,.2f}")
        lines.append(f"- Current Value: ${summary.get('total_value', 0):,.2f}")
        lines.append(f"- P&L: ${summary.get('total_pnl', 0):+,.2f} ({summary.get('total_pnl_pct', 0):+.1f}%)")
        lines.append("")

    elif report_type == "market":
        market_info = data.get('market', {})
        pricing = data.get('pricing', {})
        lines.append(f"## {market_info.get('title', 'Unknown')}")
        lines.append(f"*Category: {market_info.get('category', 'Unknown')}*")
        lines.append("")
        lines.append("### Pricing")
        lines.append(f"- Current: {pricing.get('current_price', 0):.2%}")
        lines.append(f"- 24h Change: {pricing.get('change_24h', 0):+.1f}%")
        lines.append(f"- Volume: ${pricing.get('volume_24h', 0):,.0f}")
        lines.append("")

    return "\n".join(lines)
