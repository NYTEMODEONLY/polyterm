"""Quick Summary - Fast one-line market info"""

import click
from rich.console import Console

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.argument("market_search", required=True)
@click.option("--format", "output_format", type=click.Choice(["table", "json", "oneline"]), default="oneline")
@click.pass_context
def summary(ctx, market_search, output_format):
    """Get a quick one-line market summary

    Super fast way to check a market's status.
    Perfect for quick checks and scripting.

    Examples:
        polyterm summary "bitcoin"              # Quick one-liner
        polyterm summary "trump" --format json  # JSON for scripts
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        markets = gamma_client.search_markets(market_search, limit=1)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Market not found'})
            else:
                console.print(f"[red]Not found: {market_search}[/red]")
            return

        market = markets[0]

    finally:
        gamma_client.close()

    # Extract data
    title = market.get('question', market.get('title', ''))
    price = _get_price(market)
    volume_24h = market.get('volume24hr', market.get('volume24h', 0)) or 0
    change = market.get('priceChange24h', 0)

    if not change:
        prev = market.get('price24hAgo', 0)
        if prev and prev > 0:
            change = (price - prev) / prev

    if output_format == 'json':
        print_json({
            'success': True,
            'title': title,
            'price': price,
            'price_pct': f"{price:.1%}",
            'change_24h': change,
            'change_24h_pct': f"{change:+.1%}",
            'volume_24h': volume_24h,
        })
        return

    # One-line format
    # Format: MARKET | PRICE | CHANGE | VOLUME
    short_title = title[:40] + "..." if len(title) > 40 else title

    if change > 0:
        change_str = f"[green]+{change:.1%}[/green]"
    elif change < 0:
        change_str = f"[red]{change:.1%}[/red]"
    else:
        change_str = "[dim]0%[/dim]"

    if volume_24h >= 1000000:
        vol_str = f"${volume_24h/1000000:.1f}M"
    elif volume_24h >= 1000:
        vol_str = f"${volume_24h/1000:.0f}K"
    else:
        vol_str = f"${volume_24h:.0f}"

    # Color price based on probability
    if price >= 0.7:
        price_str = f"[green]{price:.0%}[/green]"
    elif price <= 0.3:
        price_str = f"[red]{price:.0%}[/red]"
    else:
        price_str = f"[yellow]{price:.0%}[/yellow]"

    console.print(f"{short_title} | {price_str} | {change_str} | {vol_str}")


def _get_price(market: dict) -> float:
    """Get market price"""
    if market.get('outcomePrices'):
        try:
            import json
            prices = market['outcomePrices']
            if isinstance(prices, str):
                prices = json.loads(prices)
            return float(prices[0]) if prices else 0.5
        except Exception:
            pass
    return float(market.get('bestAsk', market.get('lastTradePrice', 0.5)) or 0.5)
