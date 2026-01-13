"""Screener Presets - Save and reuse search filters"""

import click
import json
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--list", "-l", "list_presets", is_flag=True, help="List all saved presets")
@click.option("--save", "-s", "save_name", default=None, help="Save current filters as preset")
@click.option("--run", "-r", "run_name", default=None, help="Run a saved preset")
@click.option("--delete", "-d", "delete_name", default=None, help="Delete a preset")
@click.option("--view", "-v", "view_name", default=None, help="View preset filters")
@click.option("--interactive", "-i", is_flag=True, help="Interactive preset creation")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def presets(ctx, list_presets, save_name, run_name, delete_name, view_name, interactive, output_format):
    """Manage saved search filter presets

    Save commonly used search filters and quickly rerun them.

    Examples:
        polyterm presets --list                    # List saved presets
        polyterm presets --save "high-volume"      # Save current filters
        polyterm presets --run "high-volume"       # Run saved preset
        polyterm presets --interactive             # Create preset interactively
        polyterm presets --delete "old-preset"     # Delete a preset
    """
    console = Console()
    db = Database()

    # Delete preset
    if delete_name:
        if db.delete_screener_preset(delete_name):
            if output_format == 'json':
                print_json({'success': True, 'action': 'deleted', 'name': delete_name})
            else:
                console.print(f"[green]Preset '{delete_name}' deleted.[/green]")
        else:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Preset not found'})
            else:
                console.print(f"[yellow]Preset '{delete_name}' not found.[/yellow]")
        return

    # View preset details
    if view_name:
        _view_preset(console, db, view_name, output_format)
        return

    # Run preset
    if run_name:
        _run_preset(console, db, run_name, output_format)
        return

    # Save preset with provided name
    if save_name:
        _interactive_save(console, db, save_name, output_format)
        return

    # Interactive mode
    if interactive:
        _interactive_create(console, db, output_format)
        return

    # Default: list presets
    _list_presets(console, db, output_format)


def _list_presets(console: Console, db: Database, output_format: str):
    """List all saved presets"""
    presets_list = db.get_screener_presets()

    if output_format == 'json':
        print_json({
            'success': True,
            'count': len(presets_list),
            'presets': presets_list,
        })
        return

    if not presets_list:
        console.print("[yellow]No saved presets yet.[/yellow]")
        console.print("[dim]Use 'polyterm presets --interactive' to create one.[/dim]")
        return

    console.print()
    console.print(Panel("[bold]Screener Presets[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Name", max_width=20)
    table.add_column("Filters", max_width=50)
    table.add_column("Created")

    for preset in presets_list:
        # Format filters preview
        filters = json.loads(preset['filters']) if isinstance(preset['filters'], str) else preset['filters']
        filter_parts = []
        if filters.get('category'):
            filter_parts.append(f"cat:{filters['category']}")
        if filters.get('min_volume'):
            filter_parts.append(f"vol>={_format_num(filters['min_volume'])}")
        if filters.get('max_volume'):
            filter_parts.append(f"vol<={_format_num(filters['max_volume'])}")
        if filters.get('min_liquidity'):
            filter_parts.append(f"liq>={_format_num(filters['min_liquidity'])}")
        if filters.get('min_price'):
            filter_parts.append(f"price>={filters['min_price']}")
        if filters.get('max_price'):
            filter_parts.append(f"price<={filters['max_price']}")
        if filters.get('ending_soon'):
            filter_parts.append(f"ending<{filters['ending_soon']}d")
        if filters.get('sort_by'):
            filter_parts.append(f"sort:{filters['sort_by']}")

        filter_str = ", ".join(filter_parts) if filter_parts else "[dim]no filters[/dim]"

        # Format date
        try:
            created = datetime.fromisoformat(preset['created_at']).strftime("%m/%d/%y")
        except Exception:
            created = preset.get('created_at', '')[:10]

        table.add_row(
            preset['name'],
            filter_str,
            created,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(presets_list)} preset(s)[/dim]")
    console.print()
    console.print("[dim]Run: polyterm presets --run <name>[/dim]")
    console.print()


def _view_preset(console: Console, db: Database, name: str, output_format: str):
    """View details of a preset"""
    preset = db.get_screener_preset(name)

    if not preset:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Preset not found'})
        else:
            console.print(f"[yellow]Preset '{name}' not found.[/yellow]")
        return

    filters = json.loads(preset['filters']) if isinstance(preset['filters'], str) else preset['filters']

    if output_format == 'json':
        print_json({
            'success': True,
            'preset': {
                'name': preset['name'],
                'filters': filters,
                'created_at': preset['created_at'],
            }
        })
        return

    console.print()
    console.print(Panel(f"[bold]Preset: {name}[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Filter", width=15)
    table.add_column("Value")

    if filters.get('category'):
        table.add_row("Category", filters['category'])
    if filters.get('min_volume'):
        table.add_row("Min Volume", f"${_format_num(filters['min_volume'])}")
    if filters.get('max_volume'):
        table.add_row("Max Volume", f"${_format_num(filters['max_volume'])}")
    if filters.get('min_liquidity'):
        table.add_row("Min Liquidity", f"${_format_num(filters['min_liquidity'])}")
    if filters.get('min_price'):
        table.add_row("Min Price", f"{filters['min_price']}")
    if filters.get('max_price'):
        table.add_row("Max Price", f"{filters['max_price']}")
    if filters.get('ending_soon'):
        table.add_row("Ending Within", f"{filters['ending_soon']} days")
    if filters.get('sort_by'):
        table.add_row("Sort By", filters['sort_by'])
    if filters.get('limit'):
        table.add_row("Limit", str(filters['limit']))
    if filters.get('query'):
        table.add_row("Search Query", filters['query'])

    console.print(table)
    console.print()

    try:
        created = datetime.fromisoformat(preset['created_at']).strftime("%Y-%m-%d %H:%M")
        console.print(f"[dim]Created: {created}[/dim]")
    except Exception:
        pass

    console.print()


def _run_preset(console: Console, db: Database, name: str, output_format: str):
    """Run a saved preset"""
    import subprocess

    preset = db.get_screener_preset(name)

    if not preset:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Preset not found'})
        else:
            console.print(f"[yellow]Preset '{name}' not found.[/yellow]")
        return

    filters = json.loads(preset['filters']) if isinstance(preset['filters'], str) else preset['filters']

    # Build search command
    cmd = ["polyterm", "search"]

    if filters.get('query'):
        cmd.extend(["--query", filters['query']])
    if filters.get('category'):
        cmd.extend(["--category", filters['category']])
    if filters.get('min_volume'):
        cmd.extend(["--min-volume", str(filters['min_volume'])])
    if filters.get('max_volume'):
        cmd.extend(["--max-volume", str(filters['max_volume'])])
    if filters.get('min_liquidity'):
        cmd.extend(["--min-liquidity", str(filters['min_liquidity'])])
    if filters.get('min_price'):
        cmd.extend(["--min-price", str(filters['min_price'])])
    if filters.get('max_price'):
        cmd.extend(["--max-price", str(filters['max_price'])])
    if filters.get('ending_soon'):
        cmd.extend(["--ending-soon", str(filters['ending_soon'])])
    if filters.get('sort_by'):
        cmd.extend(["--sort", filters['sort_by']])
    if filters.get('limit'):
        cmd.extend(["--limit", str(filters['limit'])])

    if output_format == 'json':
        cmd.extend(["--format", "json"])

    console.print(f"[dim]Running preset: {name}[/dim]")
    console.print()
    subprocess.run(cmd)


def _interactive_save(console: Console, db: Database, name: str, output_format: str):
    """Interactively create filters and save as preset"""
    console.print()
    console.print(Panel(f"[bold]Save Preset: {name}[/bold]", border_style="cyan"))
    console.print()

    filters = _collect_filters(console)

    if not any(filters.values()):
        console.print("[yellow]No filters specified. Preset not saved.[/yellow]")
        return

    db.save_screener_preset(name, filters)

    if output_format == 'json':
        print_json({'success': True, 'action': 'saved', 'name': name, 'filters': filters})
    else:
        console.print(f"[green]Preset '{name}' saved![/green]")


def _interactive_create(console: Console, db: Database, output_format: str):
    """Fully interactive preset creation"""
    console.print()
    console.print(Panel("[bold]Create Screener Preset[/bold]", border_style="cyan"))
    console.print()
    console.print("[dim]Create a reusable filter preset for market searches[/dim]")
    console.print()

    name = Prompt.ask("[cyan]Preset name[/cyan]")
    if not name:
        console.print("[yellow]No name provided.[/yellow]")
        return

    # Check for existing
    existing = db.get_screener_preset(name)
    if existing:
        if not Confirm.ask(f"[yellow]Preset '{name}' exists. Overwrite?[/yellow]"):
            return

    filters = _collect_filters(console)

    if not any(filters.values()):
        console.print("[yellow]No filters specified. Preset not saved.[/yellow]")
        return

    db.save_screener_preset(name, filters)

    if output_format == 'json':
        print_json({'success': True, 'action': 'saved', 'name': name, 'filters': filters})
    else:
        console.print()
        console.print(f"[green]Preset '{name}' saved![/green]")
        console.print(f"[dim]Run with: polyterm presets --run \"{name}\"[/dim]")


def _collect_filters(console: Console) -> dict:
    """Collect filter values from user"""
    filters = {}

    console.print("[dim]Press Enter to skip any filter[/dim]")
    console.print()

    # Query
    query = Prompt.ask("[cyan]Search query[/cyan]", default="")
    if query:
        filters['query'] = query

    # Category
    category = Prompt.ask(
        "[cyan]Category[/cyan]",
        default="",
    )
    if category:
        filters['category'] = category

    # Volume filters
    min_vol = Prompt.ask("[cyan]Minimum volume ($)[/cyan]", default="")
    if min_vol:
        try:
            filters['min_volume'] = float(min_vol)
        except ValueError:
            pass

    max_vol = Prompt.ask("[cyan]Maximum volume ($)[/cyan]", default="")
    if max_vol:
        try:
            filters['max_volume'] = float(max_vol)
        except ValueError:
            pass

    # Liquidity
    min_liq = Prompt.ask("[cyan]Minimum liquidity ($)[/cyan]", default="")
    if min_liq:
        try:
            filters['min_liquidity'] = float(min_liq)
        except ValueError:
            pass

    # Price range
    min_price = Prompt.ask("[cyan]Minimum price (0-1)[/cyan]", default="")
    if min_price:
        try:
            filters['min_price'] = float(min_price)
        except ValueError:
            pass

    max_price = Prompt.ask("[cyan]Maximum price (0-1)[/cyan]", default="")
    if max_price:
        try:
            filters['max_price'] = float(max_price)
        except ValueError:
            pass

    # Ending soon
    ending = Prompt.ask("[cyan]Ending within (days)[/cyan]", default="")
    if ending:
        try:
            filters['ending_soon'] = int(ending)
        except ValueError:
            pass

    # Sort
    sort_by = Prompt.ask(
        "[cyan]Sort by[/cyan]",
        choices=["", "volume", "liquidity", "price", "recent"],
        default=""
    )
    if sort_by:
        filters['sort_by'] = sort_by

    # Limit
    limit = Prompt.ask("[cyan]Result limit[/cyan]", default="")
    if limit:
        try:
            filters['limit'] = int(limit)
        except ValueError:
            pass

    return filters


def _format_num(num: float) -> str:
    """Format large numbers compactly"""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    return f"{num:.0f}"
