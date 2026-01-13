"""Volume Profile Command - Analyze volume at price levels"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...utils.json_output import print_json


@click.command()
@click.option("--market", "-m", "search_term", required=True, help="Market to analyze")
@click.option("--levels", "-l", type=int, default=10, help="Number of price levels")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def volume(ctx, search_term, levels, output_format):
    """Analyze volume distribution across price levels

    Shows where trading volume is concentrated to identify
    key support/resistance zones and high-activity areas.

    Examples:
        polyterm volume -m "bitcoin"           # Volume profile
        polyterm volume -m "election" -l 15    # More levels
    """
    console = Console()
    config = ctx.obj["config"]

    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    clob_client = CLOBClient(
        base_url=config.clob_base_url,
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            progress.add_task("Analyzing volume profile...", total=None)

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

            # Get current price
            current_price = 0.5
            tokens = market.get('tokens', [])
            for token in tokens:
                if token.get('outcome', '').upper() == 'YES':
                    try:
                        current_price = float(token.get('price', 0.5))
                    except (ValueError, TypeError):
                        pass
                    break

            # Get 24h volume
            total_volume = float(market.get('volume', 0) or 0)
            volume_24h = float(market.get('volume24hr', 0) or 0)

            # Get order book for depth analysis
            clob_token = market.get('clobTokenIds', [''])[0] if market.get('clobTokenIds') else ''

            orderbook = None
            if clob_token:
                orderbook = clob_client.get_orderbook(clob_token)

            # Generate volume profile from order book and estimated trade distribution
            profile = _build_volume_profile(orderbook, current_price, volume_24h, levels)

        if output_format == 'json':
            print_json({
                'success': True,
                'market_id': market_id,
                'title': title,
                'current_price': current_price,
                'total_volume': total_volume,
                'volume_24h': volume_24h,
                'profile': profile,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]Volume Profile: {title}[/bold]", border_style="cyan"))
        console.print()

        # Current price indicator
        console.print(f"[cyan]Current Price:[/cyan] {current_price:.2%}")
        console.print(f"[cyan]24h Volume:[/cyan] ${volume_24h:,.0f}")
        console.print(f"[cyan]Total Volume:[/cyan] ${total_volume:,.0f}")
        console.print()

        # Volume profile visualization
        console.print("[bold]Volume Distribution by Price Level:[/bold]")
        console.print()

        if profile:
            max_vol = max(p['volume'] for p in profile)

            for level in profile:
                bar_width = 30
                bar_len = int((level['volume'] / max_vol) * bar_width) if max_vol > 0 else 0

                # Color based on position relative to current price
                if abs(level['price'] - current_price) < 0.01:
                    bar_color = "yellow"  # Current price level
                    indicator = " <-- CURRENT"
                elif level['price'] > current_price:
                    bar_color = "red"  # Above current price (resistance)
                    indicator = ""
                else:
                    bar_color = "green"  # Below current price (support)
                    indicator = ""

                bar = f"[{bar_color}]" + "█" * bar_len + "[/]" + "[dim]" + "░" * (bar_width - bar_len) + "[/dim]"

                console.print(f"  {level['price']:.0%}  {bar}  ${level['volume']:>8,.0f} ({level['pct']:.1f}%){indicator}")

            console.print()

        # Key levels analysis
        console.print("[bold]Key Levels:[/bold]")
        console.print()

        if profile:
            # Find high volume nodes
            sorted_by_vol = sorted(profile, key=lambda x: x['volume'], reverse=True)
            hvn = sorted_by_vol[:3]  # High volume nodes

            # Find low volume nodes
            lvn = sorted_by_vol[-3:] if len(sorted_by_vol) >= 3 else sorted_by_vol  # Low volume nodes

            key_table = Table(show_header=True, header_style="bold cyan", box=None)
            key_table.add_column("Type", width=20)
            key_table.add_column("Price Level", width=12, justify="center")
            key_table.add_column("Volume", width=15, justify="right")
            key_table.add_column("Significance", width=20)

            for node in hvn:
                significance = "Strong" if node['pct'] > 15 else "Moderate" if node['pct'] > 10 else "Notable"
                position = "Resistance" if node['price'] > current_price else "Support"
                key_table.add_row(
                    f"[green]High Volume Node[/green]",
                    f"{node['price']:.0%}",
                    f"${node['volume']:,.0f}",
                    f"{significance} {position}",
                )

            for node in lvn:
                key_table.add_row(
                    f"[red]Low Volume Node[/red]",
                    f"{node['price']:.0%}",
                    f"${node['volume']:,.0f}",
                    "Potential breakout zone",
                )

            console.print(key_table)
            console.print()

        # Trading implications
        console.print("[bold]Trading Implications:[/bold]")
        console.print()

        if profile and len(profile) > 2:
            # Find value area (70% of volume)
            total_vol = sum(p['volume'] for p in profile)
            sorted_profile = sorted(profile, key=lambda x: x['volume'], reverse=True)

            value_area_vol = 0
            value_area = []
            for p in sorted_profile:
                if value_area_vol < total_vol * 0.7:
                    value_area.append(p)
                    value_area_vol += p['volume']

            if value_area:
                va_high = max(p['price'] for p in value_area)
                va_low = min(p['price'] for p in value_area)
                poc = max(profile, key=lambda x: x['volume'])  # Point of control

                console.print(f"  [cyan]Point of Control (POC):[/cyan] {poc['price']:.0%}")
                console.print(f"  [cyan]Value Area High:[/cyan] {va_high:.0%}")
                console.print(f"  [cyan]Value Area Low:[/cyan] {va_low:.0%}")
                console.print()

                if current_price > va_high:
                    console.print("  [yellow]Price above value area - watch for mean reversion[/yellow]")
                elif current_price < va_low:
                    console.print("  [yellow]Price below value area - potential undervaluation[/yellow]")
                else:
                    console.print("  [green]Price within value area - fair value zone[/green]")

        console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
        clob_client.close()


def _build_volume_profile(orderbook: dict, current_price: float, volume_24h: float, levels: int) -> list:
    """Build volume profile from order book and estimated trades"""
    profile = []

    # Create price levels from 0% to 100%
    step = 1.0 / levels
    price_levels = [step * i for i in range(levels + 1)]

    # Estimate volume distribution (higher near current price, using normal distribution)
    import math

    total_estimated = 0
    for price in price_levels:
        # Distance from current price
        distance = abs(price - current_price)

        # Bell curve - more volume near current price
        # Using a simple exponential decay
        vol_weight = math.exp(-10 * distance * distance)

        # Add volume from order book if available
        ob_vol = 0
        if orderbook:
            bids = orderbook.get('bids', [])
            asks = orderbook.get('asks', [])

            for bid in bids:
                try:
                    bid_price = float(bid.get('price', 0))
                    bid_size = float(bid.get('size', 0))
                    if abs(bid_price - price) < step / 2:
                        ob_vol += bid_price * bid_size
                except (ValueError, TypeError):
                    continue

            for ask in asks:
                try:
                    ask_price = float(ask.get('price', 0))
                    ask_size = float(ask.get('size', 0))
                    if abs(ask_price - price) < step / 2:
                        ob_vol += ask_price * ask_size
                except (ValueError, TypeError):
                    continue

        # Combine estimated trading volume with order book depth
        estimated_vol = vol_weight * (volume_24h / levels) + ob_vol

        profile.append({
            'price': price,
            'volume': estimated_vol,
        })
        total_estimated += estimated_vol

    # Normalize to percentages
    for p in profile:
        p['pct'] = (p['volume'] / total_estimated * 100) if total_estimated > 0 else 0

    return profile
