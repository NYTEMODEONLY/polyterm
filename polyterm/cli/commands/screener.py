"""Market Screener Command - Filter markets by multiple criteria"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

from ...api.gamma import GammaClient
from ...utils.json_output import print_json


@click.command()
@click.option("--min-volume", "-v", type=float, default=0, help="Minimum 24h volume ($)")
@click.option("--max-volume", type=float, default=None, help="Maximum 24h volume ($)")
@click.option("--min-price", "-p", type=float, default=0, help="Minimum YES price (0-1)")
@click.option("--max-price", type=float, default=1, help="Maximum YES price (0-1)")
@click.option("--min-liquidity", "-l", type=float, default=0, help="Minimum liquidity ($)")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--ending-within", "-e", type=int, default=None, help="Ending within N days")
@click.option("--min-change", type=float, default=None, help="Minimum 24h change (%)")
@click.option("--max-change", type=float, default=None, help="Maximum 24h change (%)")
@click.option("--sort", "-s", type=click.Choice(["volume", "price", "change", "liquidity", "end_date"]),
              default="volume", help="Sort results by")
@click.option("--limit", type=int, default=25, help="Maximum results to show")
@click.option("--interactive", "-i", is_flag=True, help="Interactive mode")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def screener(ctx, min_volume, max_volume, min_price, max_price, min_liquidity,
             category, ending_within, min_change, max_change, sort, limit,
             interactive, output_format):
    """Screen markets by multiple criteria

    Filter and find markets matching your specific requirements.
    Perfect for finding trading opportunities.

    Examples:
        polyterm screener -v 10000 -p 0.4           # High volume, mid-price
        polyterm screener --ending-within 7         # Resolving soon
        polyterm screener --min-change 5            # Big movers
        polyterm screener -i                        # Interactive mode
    """
    console = Console()
    config = ctx.obj["config"]

    if interactive:
        console.print()
        console.print(Panel("[bold]Market Screener[/bold]", border_style="cyan"))
        console.print()
        console.print("[dim]Press Enter to skip any filter[/dim]")
        console.print()

        # Volume filter
        vol_str = Prompt.ask("[cyan]Minimum 24h volume ($)[/cyan]", default="0")
        try:
            min_volume = float(vol_str)
        except ValueError:
            min_volume = 0

        max_vol_str = Prompt.ask("[cyan]Maximum 24h volume ($)[/cyan]", default="")
        if max_vol_str:
            try:
                max_volume = float(max_vol_str)
            except ValueError:
                pass

        # Price range
        console.print()
        console.print("[cyan]Price range (0-100%):[/cyan]")
        min_p_str = Prompt.ask("  Minimum price", default="0")
        max_p_str = Prompt.ask("  Maximum price", default="100")
        try:
            min_price = float(min_p_str) / 100
            max_price = float(max_p_str) / 100
        except ValueError:
            pass

        # Category
        console.print()
        category = Prompt.ask("[cyan]Category filter[/cyan]", default="")
        if not category:
            category = None

        # End date filter
        console.print()
        end_str = Prompt.ask("[cyan]Ending within (days)[/cyan]", default="")
        if end_str:
            try:
                ending_within = int(end_str)
            except ValueError:
                pass

        # Change filter
        console.print()
        change_str = Prompt.ask("[cyan]Minimum 24h change (%)[/cyan]", default="")
        if change_str:
            try:
                min_change = float(change_str)
            except ValueError:
                pass

        # Sorting
        console.print()
        console.print("[cyan]Sort by:[/cyan]")
        console.print("  1. Volume (default)")
        console.print("  2. Price")
        console.print("  3. 24h Change")
        console.print("  4. Liquidity")
        console.print("  5. End Date")
        sort_choice = Prompt.ask("Select", default="1")
        sort_map = {"1": "volume", "2": "price", "3": "change", "4": "liquidity", "5": "end_date"}
        sort = sort_map.get(sort_choice, "volume")

        # Limit
        limit_str = Prompt.ask("[cyan]Maximum results[/cyan]", default="25")
        try:
            limit = int(limit_str)
        except ValueError:
            limit = 25

        console.print()

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
            progress.add_task("Scanning markets...", total=None)

            # Fetch markets
            all_markets = gamma_client.get_markets(limit=500)

            # Apply filters
            filtered = []
            for market in all_markets:
                # Get market data
                volume_24h = float(market.get('volume24hr', 0) or 0)
                liquidity = float(market.get('liquidity', 0) or 0)

                # Get YES price
                yes_price = 0.5
                tokens = market.get('tokens', [])
                for token in tokens:
                    if token.get('outcome', '').upper() == 'YES':
                        try:
                            yes_price = float(token.get('price', 0.5))
                        except (ValueError, TypeError):
                            pass
                        break

                # Calculate 24h change
                change_24h = 0
                try:
                    prev_price = float(market.get('previousYesPrice', yes_price) or yes_price)
                    if prev_price > 0:
                        change_24h = ((yes_price - prev_price) / prev_price) * 100
                except (ValueError, TypeError):
                    pass

                # Get category
                market_category = market.get('category', '') or ''
                market_tags = market.get('tags', []) or []

                # Get end date
                end_date = market.get('endDate', '') or market.get('resolutionDate', '')

                # Apply filters
                if volume_24h < min_volume:
                    continue
                if max_volume is not None and volume_24h > max_volume:
                    continue
                if yes_price < min_price or yes_price > max_price:
                    continue
                if liquidity < min_liquidity:
                    continue
                if category and category.lower() not in market_category.lower():
                    if not any(category.lower() in tag.lower() for tag in market_tags):
                        continue
                if min_change is not None and abs(change_24h) < min_change:
                    continue
                if max_change is not None and abs(change_24h) > max_change:
                    continue

                # Check end date if filter applied
                if ending_within is not None and end_date:
                    try:
                        from datetime import datetime
                        end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                        now = datetime.now(end_dt.tzinfo)
                        days_until = (end_dt - now).days
                        if days_until < 0 or days_until > ending_within:
                            continue
                    except:
                        pass

                filtered.append({
                    'id': market.get('id', market.get('condition_id', '')),
                    'title': market.get('question', market.get('title', ''))[:50],
                    'price': yes_price,
                    'volume_24h': volume_24h,
                    'liquidity': liquidity,
                    'change_24h': change_24h,
                    'category': market_category,
                    'end_date': end_date,
                })

            # Sort results
            sort_keys = {
                'volume': lambda x: x['volume_24h'],
                'price': lambda x: x['price'],
                'change': lambda x: abs(x['change_24h']),
                'liquidity': lambda x: x['liquidity'],
                'end_date': lambda x: x['end_date'] or 'z',
            }
            filtered.sort(key=sort_keys.get(sort, lambda x: x['volume_24h']), reverse=(sort != 'end_date'))

            # Limit results
            filtered = filtered[:limit]

        if output_format == 'json':
            print_json({
                'success': True,
                'filters': {
                    'min_volume': min_volume,
                    'max_volume': max_volume,
                    'min_price': min_price,
                    'max_price': max_price,
                    'min_liquidity': min_liquidity,
                    'category': category,
                    'ending_within': ending_within,
                    'min_change': min_change,
                    'max_change': max_change,
                },
                'sort': sort,
                'total_found': len(filtered),
                'markets': filtered,
            })
            return

        # Display results
        console.print()
        console.print(Panel(f"[bold]Market Screener Results ({len(filtered)} matches)[/bold]", border_style="cyan"))
        console.print()

        # Show active filters
        filters_applied = []
        if min_volume > 0:
            filters_applied.append(f"Vol >= ${min_volume:,.0f}")
        if max_volume:
            filters_applied.append(f"Vol <= ${max_volume:,.0f}")
        if min_price > 0:
            filters_applied.append(f"Price >= {min_price:.0%}")
        if max_price < 1:
            filters_applied.append(f"Price <= {max_price:.0%}")
        if min_liquidity > 0:
            filters_applied.append(f"Liq >= ${min_liquidity:,.0f}")
        if category:
            filters_applied.append(f"Category: {category}")
        if ending_within:
            filters_applied.append(f"Ending within {ending_within}d")
        if min_change:
            filters_applied.append(f"Change >= {min_change:.1f}%")
        if max_change:
            filters_applied.append(f"Change <= {max_change:.1f}%")

        if filters_applied:
            console.print(f"[dim]Filters: {' | '.join(filters_applied)}[/dim]")
            console.print(f"[dim]Sorted by: {sort}[/dim]")
            console.print()

        if not filtered:
            console.print("[yellow]No markets match your criteria. Try adjusting filters.[/yellow]")
            return

        # Results table
        table = Table(show_header=True, header_style="bold cyan", box=None)
        table.add_column("#", width=3, justify="right")
        table.add_column("Market", width=40)
        table.add_column("Price", width=8, justify="center")
        table.add_column("24h Vol", width=12, justify="right")
        table.add_column("Change", width=8, justify="center")
        table.add_column("Liquidity", width=12, justify="right")

        for i, m in enumerate(filtered, 1):
            change_color = "green" if m['change_24h'] > 0 else "red" if m['change_24h'] < 0 else "white"

            table.add_row(
                str(i),
                m['title'],
                f"{m['price']:.0%}",
                f"${m['volume_24h']:,.0f}",
                f"[{change_color}]{m['change_24h']:+.1f}%[/{change_color}]",
                f"${m['liquidity']:,.0f}",
            )

        console.print(table)
        console.print()

        # Summary stats
        if filtered:
            avg_price = sum(m['price'] for m in filtered) / len(filtered)
            total_vol = sum(m['volume_24h'] for m in filtered)
            avg_change = sum(m['change_24h'] for m in filtered) / len(filtered)

            console.print("[bold]Summary:[/bold]")
            console.print(f"  Average Price: {avg_price:.0%}")
            console.print(f"  Total Volume: ${total_vol:,.0f}")
            console.print(f"  Average Change: {avg_change:+.1f}%")
            console.print()

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
