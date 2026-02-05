"""Market Picker - Reusable component for selecting markets"""

from typing import Optional, List, Dict, Any
from rich.console import Console as RichConsole
from rich.table import Table

from ...api.gamma import GammaClient
from ...api.aggregator import APIAggregator
from ...utils.config import Config


def fetch_markets(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch current markets from API

    Args:
        limit: Maximum number of markets to fetch

    Returns:
        List of market dictionaries
    """
    try:
        config = Config()
        # Use GammaClient directly - it's more reliable for fetching market lists
        gamma_client = GammaClient(
            base_url=config.gamma_base_url,
            api_key=config.gamma_api_key,
        )
        try:
            markets = gamma_client.get_markets(limit=limit)
            # Filter to active markets
            markets = [m for m in markets if m.get('active') and not m.get('closed')]
            return markets
        finally:
            gamma_client.close()
    except Exception:
        return []


def display_market_list(console: RichConsole, markets: List[Dict[str, Any]]) -> None:
    """Display a numbered list of markets

    Args:
        console: Rich Console instance
        markets: List of market dictionaries
    """
    table = Table(title="Available Markets", show_header=True)
    table.add_column("#", style="cyan", width=4)
    table.add_column("Market", style="white", max_width=50)
    table.add_column("Price", justify="right", style="yellow", width=8)
    table.add_column("Volume", justify="right", style="green", width=12)

    for i, market in enumerate(markets, 1):
        # Get market title
        title = market.get('title', market.get('question', 'Unknown'))[:50]

        # Get price
        price = market.get('outcomePrices', [])
        if isinstance(price, str):
            try:
                import json
                price = json.loads(price)
            except Exception:
                price = []
        yes_price = float(price[0]) if price else 0
        price_str = f"{yes_price:.0%}" if yes_price else "-"

        # Get volume
        volume = float(market.get('volume24hr', market.get('volume24Hr', 0)) or 0)
        if volume >= 1000000:
            vol_str = f"${volume/1000000:.1f}M"
        elif volume >= 1000:
            vol_str = f"${volume/1000:.1f}K"
        else:
            vol_str = f"${volume:.0f}"

        table.add_row(str(i), title, price_str, vol_str)

    console.print(table)


def pick_market(
    console: RichConsole,
    prompt: str = "Select a market",
    allow_manual: bool = True,
    limit: int = 15,
) -> Optional[Dict[str, Any]]:
    """Interactive market picker

    Args:
        console: Rich Console instance
        prompt: Prompt message to display
        allow_manual: Whether to allow manual ID entry
        limit: Number of markets to show

    Returns:
        Selected market dictionary or None if cancelled
    """
    console.print(f"\n[bold]{prompt}[/bold]\n")
    console.print("[dim]Fetching markets...[/dim]")

    # Fetch markets
    markets = fetch_markets(limit=limit)

    if not markets:
        console.print("[yellow]Could not fetch markets. Please enter ID manually.[/yellow]")
        if allow_manual:
            market_id = console.input("\n[cyan]Enter market ID or slug:[/cyan] ").strip()
            if market_id:
                return {'id': market_id, 'title': market_id, '_manual': True}
        return None

    # Display market list
    console.print()
    display_market_list(console, markets)

    # Show options
    console.print()
    if allow_manual:
        console.print("[dim]Enter number (1-{}) to select, 'm' for manual ID, or 'q' to cancel[/dim]".format(len(markets)))
    else:
        console.print("[dim]Enter number (1-{}) to select, or 'q' to cancel[/dim]".format(len(markets)))

    # Get selection
    choice = console.input("\n[cyan]Your choice:[/cyan] ").strip().lower()

    if choice == 'q' or choice == '':
        return None

    if choice == 'm' and allow_manual:
        market_id = console.input("[cyan]Enter market ID or slug:[/cyan] ").strip()
        if market_id:
            return {'id': market_id, 'title': market_id, '_manual': True}
        return None

    # Try to parse as number
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(markets):
            return markets[idx]
        else:
            console.print("[red]Invalid selection[/red]")
            return None
    except ValueError:
        console.print("[red]Invalid input[/red]")
        return None


def get_market_id(market: Dict[str, Any]) -> str:
    """Extract market ID from market dictionary

    Args:
        market: Market dictionary

    Returns:
        Market ID string
    """
    # Try different ID fields
    return (
        market.get('id') or
        market.get('conditionId') or
        market.get('condition_id') or
        market.get('slug') or
        ''
    )


def get_market_title(market: Dict[str, Any]) -> str:
    """Extract market title from market dictionary

    Args:
        market: Market dictionary

    Returns:
        Market title string
    """
    return market.get('title', market.get('question', 'Unknown Market'))
