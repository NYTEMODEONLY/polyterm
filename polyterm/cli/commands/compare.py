"""Market Comparison - Compare multiple markets side by side"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...db.database import Database
from ...core.charts import ASCIIChart
from ...utils.json_output import print_json


@click.command()
@click.option("--markets", "-m", multiple=True, help="Market IDs or search terms (can specify multiple)")
@click.option("--hours", "-h", "time_hours", default=24, help="Hours of history for comparison (default: 24)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def compare(ctx, markets, time_hours, interactive, output_format):
    """Compare multiple markets side by side

    Shows price trends, volumes, and key metrics for easy comparison.

    Examples:
        polyterm compare -m "bitcoin 100k" -m "bitcoin 90k"
        polyterm compare -i   # Interactive mode
        polyterm compare -m "trump" -m "biden" --hours 48
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    if interactive or not markets:
        result = _interactive_mode(console, config, db, time_hours)
        if result is None:
            return
        selected_markets, time_hours = result
    else:
        # Search for each market term
        gamma_client = GammaClient(
            base_url=config.gamma_base_url,
            api_key=config.gamma_api_key,
        )
        try:
            selected_markets = []
            for term in markets:
                console.print(f"[dim]Searching for: {term}[/dim]")
                results = gamma_client.search_markets(term, limit=1)
                if results:
                    selected_markets.append(results[0])
                else:
                    console.print(f"[yellow]No results for '{term}'[/yellow]")
        finally:
            gamma_client.close()

    if len(selected_markets) < 2:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Need at least 2 markets to compare'})
        else:
            console.print("[yellow]Need at least 2 markets to compare.[/yellow]")
        return

    # Track viewed markets
    import json
    for m in selected_markets:
        market_id = m.get('id', m.get('condition_id', ''))
        title = m.get('question', m.get('title', 'Unknown'))[:100]
        outcome_prices = m.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []
        price = float(outcome_prices[0]) if outcome_prices else 0.5
        db.track_market_view(market_id, title, price)

    # Gather data for comparison
    comparison_data = _gather_comparison_data(selected_markets, db, time_hours)

    if output_format == 'json':
        print_json({
            'success': True,
            'markets': comparison_data,
            'time_hours': time_hours,
        })
    else:
        _display_comparison(console, comparison_data, time_hours)


def _interactive_mode(console: Console, config, db: Database, default_hours: int):
    """Interactive market comparison"""
    console.print(Panel(
        "[bold]Market Comparison[/bold]\n\n"
        "[dim]Compare multiple markets side by side.[/dim]\n\n"
        "Search for markets you want to compare.\n"
        "You'll see price trends, volumes, and key metrics together.",
        title="[cyan]Compare[/cyan]",
        border_style="cyan",
    ))
    console.print()

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    selected_markets = []

    try:
        while len(selected_markets) < 4:  # Max 4 markets
            prompt = f"[cyan]Search for market {len(selected_markets) + 1}[/cyan]"
            if selected_markets:
                prompt += " (or press Enter to continue)"

            search_term = Prompt.ask(prompt, default="")

            if not search_term:
                if len(selected_markets) >= 2:
                    break
                else:
                    console.print("[yellow]Need at least 2 markets to compare.[/yellow]")
                    continue

            console.print(f"[dim]Searching...[/dim]")
            results = gamma_client.search_markets(search_term, limit=5)

            if not results:
                console.print(f"[yellow]No results for '{search_term}'[/yellow]")
                continue

            # Show results
            console.print()
            for i, m in enumerate(results, 1):
                title = m.get('question', m.get('title', 'Unknown'))[:50]

                # Get current price
                outcome_prices = m.get('outcomePrices', [])
                if isinstance(outcome_prices, str):
                    import json
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except Exception:
                        outcome_prices = []

                price = float(outcome_prices[0]) * 100 if outcome_prices else 50
                console.print(f"  [cyan]{i}.[/cyan] {title} [dim]({price:.0f}%)[/dim]")

            console.print()
            choice = Prompt.ask(
                "[cyan]Select market (1-5) or 's' to skip[/cyan]",
                choices=[str(i) for i in range(1, len(results) + 1)] + ['s'],
                default="1"
            )

            if choice == 's':
                continue

            selected = results[int(choice) - 1]
            market_id = selected.get('id', selected.get('condition_id', ''))

            # Check if already selected
            if any(m.get('id') == market_id for m in selected_markets):
                console.print("[yellow]Market already selected.[/yellow]")
                continue

            selected_markets.append(selected)
            title = selected.get('question', selected.get('title', ''))[:40]
            console.print(f"[green]Added: {title}[/green]")
            console.print()

        # Get time range
        console.print()
        hours_input = Prompt.ask(
            "[cyan]Hours of history to compare[/cyan]",
            default=str(default_hours)
        )
        time_hours = int(hours_input)

        return selected_markets, time_hours

    except (KeyboardInterrupt, EOFError):
        console.print("\n[yellow]Cancelled.[/yellow]")
        return None
    finally:
        gamma_client.close()


def _gather_comparison_data(markets: list, db: Database, hours: int) -> list:
    """Gather comparison data for all markets"""
    import json

    comparison = []

    for market in markets:
        market_id = market.get('id', market.get('condition_id', ''))
        title = market.get('question', market.get('title', 'Unknown'))

        # Get current price
        outcome_prices = market.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            try:
                outcome_prices = json.loads(outcome_prices)
            except Exception:
                outcome_prices = []

        current_price = float(outcome_prices[0]) if outcome_prices else 0.5

        # Get volume
        volume = float(market.get('volume', 0) or 0)
        liquidity = float(market.get('liquidity', 0) or 0)

        # Get price history
        snapshots = db.get_market_history(market_id, hours=hours)

        prices = []
        if snapshots and len(snapshots) >= 2:
            prices = [(s.timestamp, s.probability) for s in reversed(snapshots)]

        # Calculate change
        if prices and len(prices) >= 2:
            first_price = prices[0][1]
            last_price = prices[-1][1]
            change = (last_price - first_price) * 100
            change_pct = ((last_price - first_price) / first_price * 100) if first_price > 0 else 0
        else:
            change = 0
            change_pct = 0

        # Generate sparkline
        if prices:
            chart = ASCIIChart()
            values = [p for _, p in prices]
            sparkline = chart.generate_sparkline(values, width=20)
        else:
            sparkline = "─" * 20

        comparison.append({
            'id': market_id,
            'title': title[:45],
            'current_price': current_price,
            'volume': volume,
            'liquidity': liquidity,
            'change': change,
            'change_pct': change_pct,
            'sparkline': sparkline,
            'data_points': len(prices),
            'prices': prices,
        })

    return comparison


def _display_comparison(console: Console, data: list, hours: int):
    """Display comparison table"""
    console.print()
    console.print(Panel(
        f"[bold]Market Comparison[/bold] [dim](Last {hours}h)[/dim]",
        border_style="cyan",
    ))
    console.print()

    # Main comparison table
    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Market", max_width=45)
    table.add_column("Price", justify="right", width=8)
    table.add_column("Change", justify="right", width=10)
    table.add_column("Trend", width=22)
    table.add_column("Volume", justify="right", width=12)

    for m in data:
        # Color for change
        change_color = "green" if m['change'] >= 0 else "red"
        change_str = f"[{change_color}]{m['change']:+.1f}%[/{change_color}]"

        # Format volume
        if m['volume'] >= 1_000_000:
            vol_str = f"${m['volume']/1_000_000:.1f}M"
        elif m['volume'] >= 1_000:
            vol_str = f"${m['volume']/1_000:.0f}K"
        else:
            vol_str = f"${m['volume']:.0f}"

        table.add_row(
            m['title'],
            f"{m['current_price']*100:.0f}%",
            change_str,
            m['sparkline'],
            vol_str,
        )

    console.print(table)
    console.print()

    # Detailed metrics
    console.print("[bold yellow]Detailed Metrics[/bold yellow]")
    console.print()

    metrics_table = Table(show_header=True, header_style="bold", box=None)
    metrics_table.add_column("Metric", style="cyan")
    for m in data:
        # Truncate title for column header
        short_title = m['title'][:15] + "..." if len(m['title']) > 15 else m['title']
        metrics_table.add_column(short_title, justify="right")

    # Current price row
    metrics_table.add_row(
        "Current Price",
        *[f"{m['current_price']*100:.1f}%" for m in data]
    )

    # Change row
    metrics_table.add_row(
        f"Change ({hours}h)",
        *[f"[{'green' if m['change'] >= 0 else 'red'}]{m['change']:+.1f}%[/]" for m in data]
    )

    # Volume row
    def fmt_vol(v):
        if v >= 1_000_000:
            return f"${v/1_000_000:.1f}M"
        elif v >= 1_000:
            return f"${v/1_000:.0f}K"
        return f"${v:.0f}"

    metrics_table.add_row(
        "Volume",
        *[fmt_vol(m['volume']) for m in data]
    )

    # Liquidity row
    metrics_table.add_row(
        "Liquidity",
        *[fmt_vol(m['liquidity']) for m in data]
    )

    # Data points row
    metrics_table.add_row(
        "Data Points",
        *[str(m['data_points']) for m in data]
    )

    console.print(metrics_table)
    console.print()

    # Price relationship analysis
    if len(data) >= 2 and all(m['prices'] for m in data):
        console.print("[bold yellow]Price Analysis[/bold yellow]")
        console.print()

        # Sum of probabilities (for related markets)
        total_prob = sum(m['current_price'] for m in data) * 100
        console.print(f"  Combined probability: [cyan]{total_prob:.0f}%[/cyan]")

        if len(data) == 2:
            # Spread between two markets
            spread = abs(data[0]['current_price'] - data[1]['current_price']) * 100
            console.print(f"  Spread: [cyan]{spread:.1f}%[/cyan]")

            # Inverse relationship check
            sum_prob = (data[0]['current_price'] + data[1]['current_price']) * 100
            if 95 <= sum_prob <= 105:
                console.print("  [dim]These markets appear inversely related (sum near 100%)[/dim]")

        # Potential arbitrage note
        if total_prob < 95:
            console.print(f"  [yellow]Note: Combined prob < 95% - check for arbitrage[/yellow]")
        elif total_prob > 105:
            console.print(f"  [yellow]Note: Combined prob > 105% - markets may be overlapping[/yellow]")

        console.print()

    # Tips
    console.print("[dim]Tips:[/dim]")
    console.print("[dim]  - Compare related markets to spot pricing discrepancies[/dim]")
    console.print("[dim]  - If YES+NO prices sum to < 97.5%, check for arbitrage[/dim]")
    console.print("[dim]  - Use 'polyterm arbitrage' for automated detection[/dim]")
    console.print()
