"""Market Notes - Personal notes on markets"""

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
@click.option("--list", "-l", "list_notes", is_flag=True, help="List all market notes")
@click.option("--add", "-a", "add_market", default=None, help="Add note for market (ID or search)")
@click.option("--view", "-v", "view_market", default=None, help="View note for market")
@click.option("--delete", "-d", "delete_market", default=None, help="Delete note for market")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def notes(ctx, list_notes, add_market, view_market, delete_market, output_format):
    """Manage personal notes on markets

    Keep track of your research, thesis, and thoughts on markets.

    Examples:
        polyterm notes --list                    # List all notes
        polyterm notes --add "bitcoin"           # Add note for market
        polyterm notes --view "bitcoin"          # View existing note
        polyterm notes --delete "market_id"      # Delete note
    """
    console = Console()
    config = ctx.obj["config"]
    db = Database()

    # Delete note
    if delete_market:
        if db.delete_market_note(delete_market):
            if output_format == 'json':
                print_json({'success': True, 'action': 'deleted', 'market_id': delete_market})
            else:
                console.print(f"[green]Note deleted.[/green]")
        else:
            if output_format == 'json':
                print_json({'success': False, 'error': 'Note not found'})
            else:
                console.print(f"[yellow]Note not found for that market.[/yellow]")
        return

    # View specific note
    if view_market:
        _view_note(console, config, db, view_market, output_format)
        return

    # Add note
    if add_market:
        _add_note(console, config, db, add_market, output_format)
        return

    # List notes (default)
    _list_notes(console, db, output_format)


def _list_notes(console: Console, db: Database, output_format: str):
    """List all market notes"""
    notes_list = db.get_all_market_notes()

    if output_format == 'json':
        print_json({
            'success': True,
            'count': len(notes_list),
            'notes': notes_list,
        })
        return

    if not notes_list:
        console.print("[yellow]No market notes yet.[/yellow]")
        console.print("[dim]Use 'polyterm notes --add <market>' to add notes.[/dim]")
        return

    console.print()
    console.print(Panel("[bold]Market Notes[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("Market", max_width=45)
    table.add_column("Note Preview", max_width=30)
    table.add_column("Updated", width=12)

    for note in notes_list:
        # Format time
        try:
            updated = datetime.fromisoformat(note['updated_at'])
            time_str = updated.strftime("%m/%d %H:%M")
        except Exception:
            time_str = note.get('updated_at', '')[:10]

        # Truncate note preview
        note_preview = note['notes'][:28] + "..." if len(note['notes']) > 28 else note['notes']
        note_preview = note_preview.replace('\n', ' ')

        table.add_row(
            note['title'][:43],
            note_preview,
            time_str,
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(notes_list)} note(s)[/dim]")
    console.print()


def _view_note(console: Console, config, db: Database, search_term: str, output_format: str):
    """View a specific note"""
    # First try direct market ID lookup
    note = db.get_market_note(search_term)

    if not note:
        # Try searching for market
        gamma_client = GammaClient(
            base_url=config.gamma_base_url,
            api_key=config.gamma_api_key,
        )

        try:
            markets = gamma_client.search_markets(search_term, limit=1)
            if markets:
                market_id = markets[0].get('id', markets[0].get('condition_id', ''))
                note = db.get_market_note(market_id)
        finally:
            gamma_client.close()

    if not note:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Note not found'})
        else:
            console.print(f"[yellow]No note found for '{search_term}'[/yellow]")
        return

    if output_format == 'json':
        print_json({
            'success': True,
            'note': note,
        })
        return

    console.print()
    console.print(Panel(f"[bold]{note['title']}[/bold]", border_style="cyan"))
    console.print()
    console.print(note['notes'])
    console.print()

    # Format timestamps
    try:
        created = datetime.fromisoformat(note['created_at']).strftime("%Y-%m-%d %H:%M")
        updated = datetime.fromisoformat(note['updated_at']).strftime("%Y-%m-%d %H:%M")
        console.print(f"[dim]Created: {created}[/dim]")
        console.print(f"[dim]Updated: {updated}[/dim]")
    except Exception:
        pass

    console.print()


def _add_note(console: Console, config, db: Database, search_term: str, output_format: str):
    """Add or edit a note for a market"""
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    try:
        console.print(f"[dim]Searching for: {search_term}[/dim]")
        markets = gamma_client.search_markets(search_term, limit=5)

        if not markets:
            if output_format == 'json':
                print_json({'success': False, 'error': f'No markets found for "{search_term}"'})
            else:
                console.print(f"[yellow]No markets found for '{search_term}'[/yellow]")
            return

        # Select market
        if len(markets) > 1 and output_format != 'json':
            console.print()
            console.print("[bold]Multiple markets found:[/bold]")
            for i, m in enumerate(markets, 1):
                title = m.get('question', m.get('title', 'Unknown'))[:50]
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
        title = selected.get('question', selected.get('title', ''))[:100]

        # Check for existing note
        existing = db.get_market_note(market_id)

        console.print()
        console.print(f"[bold]{title}[/bold]")
        console.print()

        if existing:
            console.print("[dim]Existing note:[/dim]")
            console.print(f"[dim]{existing['notes'][:200]}...[/dim]" if len(existing['notes']) > 200 else f"[dim]{existing['notes']}[/dim]")
            console.print()

        console.print("[dim]Enter your note (multi-line supported, end with empty line):[/dim]")

        lines = []
        while True:
            line = Prompt.ask("", default="")
            if not line and lines:
                break
            lines.append(line)

        note_text = '\n'.join(lines).strip()

        if not note_text:
            console.print("[yellow]No note entered.[/yellow]")
            return

        db.set_market_note(market_id, title, note_text)

        if output_format == 'json':
            print_json({
                'success': True,
                'action': 'saved',
                'market_id': market_id,
            })
        else:
            action = "updated" if existing else "added"
            console.print(f"[green]Note {action}![/green]")

    except Exception as e:
        if output_format == 'json':
            print_json({'success': False, 'error': str(e)})
        else:
            console.print(f"[red]Error: {e}[/red]")
    finally:
        gamma_client.close()
