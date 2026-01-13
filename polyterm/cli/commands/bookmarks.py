"""Bookmarks command - Save and manage favorite markets"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt

from ...api.gamma import GammaClient
from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--list", "list_bookmarks", is_flag=True, help="List all bookmarked markets")
@click.option("--add", "-a", default=None, help="Add a market to bookmarks (ID or search term)")
@click.option("--remove", "-r", default=None, help="Remove a market from bookmarks")
@click.option("--notes", "-n", default=None, help="Add notes to a bookmark")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def bookmarks(ctx, list_bookmarks, add, remove, notes, output_format):
    """Manage bookmarked markets

    Save markets you want to track or revisit later.

    Examples:
        polyterm bookmarks --list              # List all bookmarks
        polyterm bookmarks --add "bitcoin"     # Bookmark a market
        polyterm bookmarks --remove <market_id>  # Remove bookmark
    """
    console = Console()
    db = Database()
    config = ctx.obj["config"]

    # If no options, show interactive menu or list
    if not list_bookmarks and not add and not remove:
        _interactive_mode(console, db, config)
        return

    # List bookmarks
    if list_bookmarks:
        saved = db.get_bookmarks()

        if output_format == 'json':
            print_json({
                'success': True,
                'count': len(saved),
                'bookmarks': saved,
            })
            return

        if not saved:
            console.print("[yellow]No bookmarks yet.[/yellow]")
            console.print("[dim]Use 'polyterm bookmarks --add <market>' to save a market.[/dim]")
            return

        _display_bookmarks(console, saved)
        return

    # Add a bookmark
    if add:
        gamma_client = GammaClient(
            base_url=config.gamma_base_url,
            api_key=config.gamma_api_key,
        )

        try:
            # Search for the market
            markets = gamma_client.search_markets(add, limit=5)

            if not markets:
                if output_format == 'json':
                    print_json({'success': False, 'error': f"No markets found matching '{add}'"})
                else:
                    console.print(f"[yellow]No markets found matching '{add}'[/yellow]")
                return

            # If multiple results in non-json mode, let user choose
            if len(markets) > 1 and output_format != 'json':
                console.print()
                console.print("[bold]Multiple markets found:[/bold]")
                for i, m in enumerate(markets, 1):
                    title = m.get('question', m.get('title', 'Unknown'))[:55]
                    console.print(f"  [cyan]{i}.[/cyan] {title}")

                console.print()
                choice = Prompt.ask(
                    "[cyan]Select market to bookmark[/cyan]",
                    choices=[str(i) for i in range(1, len(markets) + 1)],
                    default="1"
                )
                selected = markets[int(choice) - 1]
            else:
                selected = markets[0]

            market_id = selected.get('id', selected.get('condition_id', ''))
            title = selected.get('question', selected.get('title', ''))
            category = selected.get('category', '')

            # Get probability
            outcome_prices = selected.get('outcomePrices', [])
            if isinstance(outcome_prices, str):
                import json
                try:
                    outcome_prices = json.loads(outcome_prices)
                except Exception:
                    outcome_prices = []
            probability = float(outcome_prices[0]) if outcome_prices else 0

            # Check if already bookmarked
            if db.is_bookmarked(market_id):
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Market already bookmarked'})
                else:
                    console.print(f"[yellow]'{title[:40]}...' is already bookmarked.[/yellow]")
                return

            # Add bookmark
            db.bookmark_market(market_id, title, category, probability, notes or "")

            if output_format == 'json':
                print_json({
                    'success': True,
                    'action': 'bookmarked',
                    'market_id': market_id,
                    'title': title,
                })
            else:
                console.print(f"[green]Bookmarked: {title[:50]}[/green]")
                if notes:
                    console.print(f"[dim]Notes: {notes}[/dim]")

        finally:
            gamma_client.close()

        return

    # Remove a bookmark
    if remove:
        if not db.is_bookmarked(remove):
            # Try searching by partial match
            bookmarks_list = db.get_bookmarks()
            matching = [b for b in bookmarks_list if remove.lower() in b['title'].lower() or b['market_id'] == remove]

            if not matching:
                if output_format == 'json':
                    print_json({'success': False, 'error': 'Bookmark not found'})
                else:
                    console.print(f"[yellow]No bookmark found matching '{remove}'[/yellow]")
                return

            if len(matching) == 1:
                remove = matching[0]['market_id']
            else:
                console.print()
                console.print("[bold]Multiple matches found:[/bold]")
                for i, b in enumerate(matching, 1):
                    console.print(f"  [cyan]{i}.[/cyan] {b['title'][:50]}")
                console.print()
                choice = Prompt.ask(
                    "[cyan]Select bookmark to remove[/cyan]",
                    choices=[str(i) for i in range(1, len(matching) + 1)],
                    default="1"
                )
                remove = matching[int(choice) - 1]['market_id']

        bookmark = db.get_bookmark(remove)
        db.remove_bookmark(remove)

        if output_format == 'json':
            print_json({'success': True, 'action': 'removed', 'market_id': remove})
        else:
            title = bookmark['title'] if bookmark else remove
            console.print(f"[green]Removed bookmark: {title[:50]}[/green]")


def _interactive_mode(console: Console, db: Database, config):
    """Interactive bookmark management"""
    console.clear()
    console.print(Panel(
        "[bold]Market Bookmarks[/bold]\n\n"
        "[dim]Save markets you want to track or revisit later.[/dim]",
        title="[cyan]Bookmarks[/cyan]",
        border_style="cyan",
    ))
    console.print()

    while True:
        saved = db.get_bookmarks()

        console.print(f"[cyan]Saved: {len(saved)} markets[/cyan]")
        console.print()
        console.print("  [bold]1.[/bold] View bookmarks")
        console.print("  [bold]2.[/bold] Add bookmark")
        console.print("  [bold]3.[/bold] Remove bookmark")
        console.print("  [bold]4.[/bold] Add notes to bookmark")
        console.print("  [bold]q.[/bold] Return to menu")
        console.print()

        choice = Prompt.ask("[cyan]Select option[/cyan]", choices=["1", "2", "3", "4", "q"], default="1")

        if choice == "q":
            break

        if choice == "1":
            console.print()
            if not saved:
                console.print("[yellow]No bookmarks yet.[/yellow]")
            else:
                _display_bookmarks(console, saved)

        elif choice == "2":
            console.print()
            search = Prompt.ask("[cyan]Enter market name or ID to bookmark[/cyan]")
            if search:
                gamma_client = GammaClient(
                    base_url=config.gamma_base_url,
                    api_key=config.gamma_api_key,
                )
                try:
                    markets = gamma_client.search_markets(search, limit=5)
                    if not markets:
                        console.print("[yellow]No markets found.[/yellow]")
                    else:
                        if len(markets) > 1:
                            console.print()
                            console.print("[bold]Select market:[/bold]")
                            for i, m in enumerate(markets, 1):
                                title = m.get('question', m.get('title', ''))[:50]
                                console.print(f"  [cyan]{i}.[/cyan] {title}")
                            console.print()
                            idx = Prompt.ask(
                                "[cyan]Select[/cyan]",
                                choices=[str(i) for i in range(1, len(markets) + 1)],
                                default="1"
                            )
                            selected = markets[int(idx) - 1]
                        else:
                            selected = markets[0]

                        market_id = selected.get('id', selected.get('condition_id', ''))
                        title = selected.get('question', selected.get('title', ''))

                        if db.is_bookmarked(market_id):
                            console.print("[yellow]Already bookmarked.[/yellow]")
                        else:
                            notes = Prompt.ask("[cyan]Add notes (optional)[/cyan]", default="")
                            db.bookmark_market(market_id, title, selected.get('category', ''), 0, notes)
                            console.print(f"[green]Bookmarked: {title[:40]}[/green]")
                finally:
                    gamma_client.close()

        elif choice == "3":
            console.print()
            if not saved:
                console.print("[yellow]No bookmarks to remove.[/yellow]")
            else:
                console.print("[bold]Select bookmark to remove:[/bold]")
                for i, b in enumerate(saved, 1):
                    console.print(f"  [cyan]{i}.[/cyan] {b['title'][:50]}")
                console.print()
                idx = Prompt.ask(
                    "[cyan]Select[/cyan]",
                    choices=[str(i) for i in range(1, len(saved) + 1)] + ["q"],
                    default="q"
                )
                if idx != "q":
                    bookmark = saved[int(idx) - 1]
                    db.remove_bookmark(bookmark['market_id'])
                    console.print(f"[green]Removed: {bookmark['title'][:40]}[/green]")

        elif choice == "4":
            console.print()
            if not saved:
                console.print("[yellow]No bookmarks to edit.[/yellow]")
            else:
                console.print("[bold]Select bookmark to add notes:[/bold]")
                for i, b in enumerate(saved, 1):
                    notes_preview = f" - {b['notes'][:20]}..." if b.get('notes') else ""
                    console.print(f"  [cyan]{i}.[/cyan] {b['title'][:40]}{notes_preview}")
                console.print()
                idx = Prompt.ask(
                    "[cyan]Select[/cyan]",
                    choices=[str(i) for i in range(1, len(saved) + 1)] + ["q"],
                    default="q"
                )
                if idx != "q":
                    bookmark = saved[int(idx) - 1]
                    current = bookmark.get('notes', '')
                    if current:
                        console.print(f"[dim]Current notes: {current}[/dim]")
                    new_notes = Prompt.ask("[cyan]Enter notes[/cyan]", default=current)
                    db.update_bookmark_notes(bookmark['market_id'], new_notes)
                    console.print("[green]Notes updated.[/green]")

        console.print()


def _display_bookmarks(console: Console, bookmarks: list):
    """Display bookmarks in a table"""
    table = Table(title="Bookmarked Markets", show_header=True)
    table.add_column("#", justify="right", style="dim", width=3)
    table.add_column("Market", style="cyan", max_width=45)
    table.add_column("Category", style="dim")
    table.add_column("Notes", style="yellow", max_width=20)

    for i, b in enumerate(bookmarks, 1):
        title = b['title'][:45] if len(b['title']) > 45 else b['title']
        notes = b.get('notes', '')
        notes_display = notes[:20] + "..." if len(notes) > 20 else notes

        table.add_row(
            str(i),
            title,
            b.get('category', '-'),
            notes_display or "[dim]-[/dim]",
        )

    console.print(table)
    console.print()
    console.print("[dim]Tip: Use 'polyterm watch --market <id>' to track a bookmarked market.[/dim]")
