"""Chart command - Visualize market price history"""

import click
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...db.database import Database
from ...core.charts import ASCIIChart, generate_price_chart
from ...utils.json_output import print_json, safe_float


def _parse_clob_token_ids(raw_token_ids):
    """Normalize clobTokenIds to a list of token ids."""
    token_ids = raw_token_ids
    if isinstance(token_ids, str):
        import json as json_mod
        try:
            token_ids = json_mod.loads(token_ids)
        except Exception:
            return []

    if not isinstance(token_ids, list):
        return []

    return [token_id for token_id in token_ids if token_id]


def _select_clob_granularity(time_hours):
    """Pick CLOB interval/fidelity based on requested window."""
    if time_hours <= 1:
        return "1h", 60
    if time_hours <= 6:
        return "6h", 60
    if time_hours <= 24:
        return "1d", 300
    return "max", 3600


def _build_time_bounds(time_hours):
    """Build [start, end] unix timestamp bounds for the requested window."""
    hours = max(int(time_hours), 1)
    end_ts = int(datetime.now().timestamp())
    start_ts = end_ts - (hours * 3600)
    return start_ts, end_ts


def _parse_clob_prices(history, start_ts, end_ts):
    """Convert CLOB history rows into chart points within the requested bounds."""
    prices = []

    for row in history or []:
        if "t" not in row or "p" not in row:
            continue
        try:
            timestamp = int(row["t"])
        except (TypeError, ValueError):
            continue
        if timestamp < start_ts or timestamp > end_ts:
            continue
        prices.append((datetime.fromtimestamp(timestamp), safe_float(row["p"])))

    prices.sort(key=lambda point: point[0])
    return prices


@click.command()
@click.option("--market", "-m", default=None, help="Market ID or search term")
@click.option("--hours", "-h", "time_hours", default=24, help="Hours of history (default: 24)")
@click.option("--width", "-w", default=50, help="Chart width (default: 50)")
@click.option("--height", default=12, help="Chart height (default: 12)")
@click.option("--sparkline", "-s", is_flag=True, help="Show compact sparkline instead of full chart")
@click.option("--format", "output_format", type=click.Choice(["chart", "json"]), default="chart")
@click.pass_context
def chart(ctx, market, time_hours, width, height, sparkline, output_format):
    """Display price history chart for a market

    Shows ASCII chart of price movement over time.

    Examples:
        polyterm chart --market "bitcoin"
        polyterm chart -m "election" --hours 48
        polyterm chart -m "bitcoin" --sparkline
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    if not market:
        console.print(Panel(
            "[bold]Price Chart[/bold]\n\n"
            "[dim]Visualize market price history in the terminal.[/dim]",
            title="[cyan]Chart[/cyan]",
            border_style="cyan",
        ))
        console.print()
        market = Prompt.ask("[cyan]Enter market ID or search term[/cyan]")

    if not market:
        console.print("[yellow]No market specified.[/yellow]")
        return

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        # Search for market
        console.print(f"[dim]Searching for: {market}[/dim]")
        markets = gamma_client.search_markets(market, limit=5)

        if not markets:
            console.print(f"[yellow]No markets found matching '{market}'[/yellow]")
            return

        # Select market if multiple
        if len(markets) > 1 and output_format != 'json':
            console.print()
            console.print("[bold]Multiple markets found:[/bold]")
            for i, m in enumerate(markets, 1):
                title = m.get('question', m.get('title', 'Unknown'))[:55]
                console.print(f"  [cyan]{i}.[/cyan] {title}")

            console.print()
            choice = Prompt.ask(
                "[cyan]Select market[/cyan]",
                choices=[str(i) for i in range(1, len(markets) + 1)],
                default="1"
            )
            selected = markets[int(choice) - 1]
        else:
            selected = markets[0]

        market_id = selected.get('id', selected.get('condition_id', ''))
        title = selected.get('question', selected.get('title', ''))[:50]

        # Get current price for tracking
        outcome_prices = selected.get('outcomePrices', [])
        if isinstance(outcome_prices, str):
            import json as json_mod
            try:
                outcome_prices = json_mod.loads(outcome_prices)
            except Exception:
                outcome_prices = []
        current_price = float(outcome_prices[0]) if outcome_prices else 0.5

        # Track this market view
        db.track_market_view(market_id, title, current_price)

        # Try CLOB price history first (real market data)
        prices = None
        clob_token_ids = _parse_clob_token_ids(selected.get('clobTokenIds', []))

        if clob_token_ids:
            clob_client = None
            try:
                clob_client = CLOBClient(
                    rest_endpoint=config.clob_rest_endpoint,
                )
                interval, fidelity = _select_clob_granularity(time_hours)
                start_ts, end_ts = _build_time_bounds(time_hours)

                history = clob_client.get_price_history(
                    clob_token_ids[0],
                    interval=interval,
                    fidelity=fidelity,
                    start_ts=start_ts,
                    end_ts=end_ts,
                )
                prices = _parse_clob_prices(history, start_ts=start_ts, end_ts=end_ts)
                if len(prices) >= 2:
                    if output_format != 'json':
                        console.print(f"[dim]Using CLOB price history ({len(prices)} points)[/dim]")
            except Exception:
                pass  # Fall back to DB snapshots
            finally:
                if clob_client is not None:
                    clob_client.close()

        # Fall back to database snapshots
        if not prices or len(prices) < 2:
            snapshots = db.get_market_history(market_id, hours=time_hours)
            if snapshots and len(snapshots) >= 2:
                prices = [(s.timestamp, s.probability) for s in reversed(snapshots)]

        # Last resort: flat line at current price
        if not prices or len(prices) < 2:
            if output_format != 'json':
                console.print("[yellow]No price history available. Showing current price only.[/yellow]")
            now = datetime.now()
            prices = [
                (now - timedelta(hours=time_hours), current_price),
                (now, current_price),
            ]

        # JSON output
        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'hours': time_hours,
                'data_points': len(prices),
                'prices': [
                    {'timestamp': ts.isoformat(), 'price': p}
                    for ts, p in prices
                ],
            })
            return

        console.print()

        if sparkline:
            # Compact sparkline
            chart_gen = ASCIIChart()
            values = [p for _, p in prices]
            spark = chart_gen.generate_sparkline(values, width=40)

            current = values[-1] * 100 if values else 0
            change = ((values[-1] - values[0]) / values[0] * 100) if values and values[0] > 0 else 0
            change_color = "green" if change >= 0 else "red"

            console.print(f"[bold]{title}[/bold]")
            console.print(f"  {spark} [{change_color}]{current:.0f}% ({change:+.1f}%)[/{change_color}]")
            console.print(f"  [dim]Last {time_hours}h ({len(prices)} data points)[/dim]")
        else:
            # Full chart
            chart_str = generate_price_chart(
                prices,
                title=f"{title} (Last {time_hours}h)",
                width=width,
                height=height,
            )
            console.print(chart_str)

            # Stats
            values = [p * 100 for _, p in prices]
            if values:
                console.print()
                console.print(f"[bold]Stats:[/bold]")
                console.print(f"  Current: [cyan]{values[-1]:.1f}%[/cyan]")
                console.print(f"  High: [green]{max(values):.1f}%[/green]")
                console.print(f"  Low: [red]{min(values):.1f}%[/red]")

                change = values[-1] - values[0]
                change_color = "green" if change >= 0 else "red"
                console.print(f"  Change: [{change_color}]{change:+.1f}%[/{change_color}]")

        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
