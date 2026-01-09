"""Analytics Screen - Market insights and analysis"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
from datetime import datetime, timezone

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...api.aggregator import APIAggregator
from ...utils.config import Config


def _display_trending_markets(console: RichConsole, limit: int = 10):
    """Display trending markets by 24hr volume

    Args:
        console: Rich Console instance
        limit: Number of markets to display
    """
    # Initialize config and API clients
    config = Config()

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )
    subgraph_client = SubgraphClient(endpoint=config.subgraph_endpoint)

    aggregator = APIAggregator(gamma_client, clob_client, subgraph_client)

    try:
        # Get top markets by volume with meaningful threshold ($1000+ 24hr volume)
        markets = aggregator.get_top_markets_by_volume(limit=limit, min_volume=1000)

        if not markets:
            console.print("[yellow]No trending markets found with significant volume.[/yellow]")
            console.print("[dim]Try again later or check your connection.[/dim]")
            return

        # Build the table
        now = datetime.now()
        table = Table(title=f"Trending Markets by 24hr Volume (as of {now.strftime('%H:%M:%S')})")

        table.add_column("#", style="dim", justify="right", width=3)
        table.add_column("Market", style="cyan", no_wrap=False, max_width=50)
        table.add_column("Probability", justify="right", style="green")
        table.add_column("24hr Volume", justify="right", style="yellow")
        table.add_column("Ends", justify="right", style="dim")

        for idx, market in enumerate(markets, 1):
            title = market.get("question", market.get("title", ""))[:50]

            # Get probability from outcome prices
            outcome_prices = market.get('outcomePrices')
            if not outcome_prices and market.get('markets') and len(market.get('markets', [])) > 0:
                outcome_prices = market['markets'][0].get('outcomePrices')

            # Parse outcome prices (can be string or list)
            if isinstance(outcome_prices, str):
                import json
                try:
                    outcome_prices = json.loads(outcome_prices)
                except:
                    outcome_prices = None

            if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                price = float(outcome_prices[0])
            else:
                price = 0

            probability = price * 100 if price else 0
            volume_24hr = float(market.get('volume24hr', 0) or 0)

            # Calculate time until market ends
            end_date_str = market.get('endDate', '')
            ends_text = "Unknown"
            if end_date_str:
                try:
                    from dateutil import parser as date_parser
                    end_date = date_parser.parse(end_date_str)
                    now_utc = datetime.now(timezone.utc)

                    hours_until = (end_date - now_utc).total_seconds() / 3600
                    if hours_until < 0:
                        ends_text = "[red]Ended[/red]"
                    elif hours_until < 24:
                        ends_text = f"{int(hours_until)}h"
                    elif hours_until < 24 * 7:
                        ends_text = f"{int(hours_until / 24)}d"
                    elif hours_until < 24 * 30:
                        ends_text = f"{int(hours_until / 24 / 7)}w"
                    else:
                        ends_text = f"{int(hours_until / 24 / 30)}mo"
                except Exception:
                    ends_text = "?"

            # Format probability with color
            prob_style = "green" if probability > 50 else "yellow" if probability > 30 else "white"
            prob_text = f"[{prob_style}]{probability:.1f}%[/{prob_style}]"

            # Format volume
            if volume_24hr >= 1_000_000:
                volume_text = f"${volume_24hr/1_000_000:.1f}M"
            elif volume_24hr >= 1_000:
                volume_text = f"${volume_24hr/1_000:.1f}K"
            else:
                volume_text = f"${volume_24hr:,.0f}"

            table.add_row(
                str(idx),
                title,
                prob_text,
                volume_text,
                ends_text,
            )

        console.print(table)
        console.print()
        console.print(f"[dim]Showing top {len(markets)} markets by 24-hour trading volume[/dim]")

    except Exception as e:
        console.print(f"[red]Error fetching trending markets: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()


def analytics_screen(console: RichConsole):
    """Market analytics and insights

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Market Analytics[/bold]", style="cyan"))
    console.print()

    # Submenu for analytics
    console.print("[bold]Select Analytics Type:[/bold]")
    console.print()

    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")

    menu.add_row("1", "Trending Markets - Most active by 24hr volume")
    menu.add_row("2", "Market Correlations - Related markets")
    menu.add_row("3", "Price Predictions - Trend analysis")
    menu.add_row("4", "Volume Analysis - Volume patterns")
    menu.add_row("", "")
    menu.add_row("b", "Back - Return to main menu")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-4, b):[/cyan] ").strip().lower()
    console.print()

    if choice == '1':
        # Trending Markets
        limit = console.input("How many markets? [cyan][default: 10][/cyan] ").strip() or "10"
        try:
            limit = int(limit)
            if limit < 1:
                limit = 10
            elif limit > 50:
                limit = 50
        except ValueError:
            limit = 10

        console.print()
        console.print("[green]Fetching trending markets...[/green]")
        console.print()

        _display_trending_markets(console, limit)

    elif choice == '2':
        # Market Correlations
        console.print("[yellow]Market correlation analysis coming soon![/yellow]")
        console.print("[dim]This feature will show markets that tend to move together.[/dim]")

    elif choice == '3':
        # Price Predictions
        console.print("[yellow]Price prediction analysis coming soon![/yellow]")
        console.print("[dim]This feature will analyze price trends and momentum.[/dim]")

    elif choice == '4':
        # Volume Analysis
        console.print("[yellow]Volume analysis coming soon![/yellow]")
        console.print("[dim]This feature will identify volume patterns and spikes.[/dim]")

    elif choice == 'b':
        return

    else:
        console.print("[red]Invalid option[/red]")
