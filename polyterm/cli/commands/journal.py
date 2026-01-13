"""Trade Journal - Document and learn from your trades"""

import click
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown

from ...db.database import Database
from ...utils.json_output import print_json


@click.command()
@click.option("--list", "-l", "list_entries", is_flag=True, help="List journal entries")
@click.option("--add", "-a", is_flag=True, help="Add new journal entry")
@click.option("--view", "-v", type=int, default=None, help="View entry by ID")
@click.option("--delete", "-d", type=int, default=None, help="Delete entry by ID")
@click.option("--search", "-s", default=None, help="Search entries")
@click.option("--tag", "-t", default=None, help="Filter by tag")
@click.option("--limit", default=20, help="Number of entries to show")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table")
@click.pass_context
def journal(ctx, list_entries, add, view, delete, search, tag, limit, output_format):
    """Trade journal for documenting your trades

    Keep track of your trading decisions, lessons learned,
    and insights for continuous improvement.

    Examples:
        polyterm journal --list               # List entries
        polyterm journal --add                # Add new entry
        polyterm journal --view 1             # View entry #1
        polyterm journal --search "bitcoin"   # Search entries
        polyterm journal --tag "lesson"       # Filter by tag
    """
    console = Console()
    db = Database()

    # Initialize journal table
    _init_journal_table(db)

    # Delete entry
    if delete:
        _delete_entry(console, db, delete, output_format)
        return

    # View entry
    if view:
        _view_entry(console, db, view, output_format)
        return

    # Add entry
    if add:
        _add_entry(console, db, output_format)
        return

    # Search
    if search:
        _search_entries(console, db, search, limit, output_format)
        return

    # Filter by tag
    if tag:
        _filter_by_tag(console, db, tag, limit, output_format)
        return

    # Default: list entries
    _list_entries(console, db, limit, output_format)


def _init_journal_table(db: Database):
    """Initialize journal table"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_journal (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                market_id TEXT DEFAULT '',
                entry_type TEXT DEFAULT 'note',
                content TEXT NOT NULL,
                tags TEXT DEFAULT '',
                outcome TEXT DEFAULT '',
                lesson TEXT DEFAULT '',
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)


def _list_entries(console: Console, db: Database, limit: int, output_format: str):
    """List journal entries"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trade_journal ORDER BY created_at DESC LIMIT ?
        """, (limit,))
        entries = [dict(row) for row in cursor.fetchall()]

    if output_format == 'json':
        print_json({'success': True, 'count': len(entries), 'entries': entries})
        return

    if not entries:
        console.print("[yellow]No journal entries yet.[/yellow]")
        console.print("[dim]Use 'polyterm journal --add' to create one.[/dim]")
        return

    console.print()
    console.print(Panel("[bold]Trade Journal[/bold]", border_style="cyan"))
    console.print()

    table = Table(show_header=True, header_style="bold cyan", box=None)
    table.add_column("ID", width=4)
    table.add_column("Date", width=10)
    table.add_column("Type", width=8)
    table.add_column("Title", max_width=35)
    table.add_column("Tags", max_width=15)

    for entry in entries:
        # Format date
        try:
            date = datetime.fromisoformat(entry['created_at']).strftime("%m/%d/%y")
        except Exception:
            date = entry['created_at'][:10]

        # Type color
        entry_type = entry.get('entry_type', 'note')
        if entry_type == 'win':
            type_str = "[green]WIN[/green]"
        elif entry_type == 'loss':
            type_str = "[red]LOSS[/red]"
        elif entry_type == 'lesson':
            type_str = "[yellow]LESSON[/yellow]"
        else:
            type_str = "[dim]note[/dim]"

        tags = entry.get('tags', '')[:13]

        table.add_row(
            str(entry['id']),
            date,
            type_str,
            entry['title'][:33],
            f"[dim]{tags}[/dim]" if tags else "",
        )

    console.print(table)
    console.print()
    console.print(f"[dim]{len(entries)} entries shown[/dim]")
    console.print()


def _view_entry(console: Console, db: Database, entry_id: int, output_format: str):
    """View a journal entry"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM trade_journal WHERE id = ?", (entry_id,))
        row = cursor.fetchone()

    if not row:
        if output_format == 'json':
            print_json({'success': False, 'error': 'Entry not found'})
        else:
            console.print(f"[yellow]Entry #{entry_id} not found.[/yellow]")
        return

    entry = dict(row)

    if output_format == 'json':
        print_json({'success': True, 'entry': entry})
        return

    console.print()

    # Type badge
    entry_type = entry.get('entry_type', 'note')
    if entry_type == 'win':
        badge = "[green]WIN[/green]"
    elif entry_type == 'loss':
        badge = "[red]LOSS[/red]"
    elif entry_type == 'lesson':
        badge = "[yellow]LESSON[/yellow]"
    else:
        badge = "[dim]note[/dim]"

    console.print(Panel(f"[bold]{entry['title']}[/bold] {badge}", border_style="cyan"))
    console.print()

    # Content
    console.print(entry['content'])
    console.print()

    # Outcome
    if entry.get('outcome'):
        console.print("[bold]Outcome:[/bold]")
        console.print(f"  {entry['outcome']}")
        console.print()

    # Lesson
    if entry.get('lesson'):
        console.print("[bold yellow]Lesson Learned:[/bold yellow]")
        console.print(f"  {entry['lesson']}")
        console.print()

    # Metadata
    console.print("[dim]---[/dim]")
    if entry.get('tags'):
        console.print(f"[dim]Tags: {entry['tags']}[/dim]")
    if entry.get('market_id'):
        console.print(f"[dim]Market: {entry['market_id']}[/dim]")

    try:
        created = datetime.fromisoformat(entry['created_at']).strftime("%Y-%m-%d %H:%M")
        console.print(f"[dim]Created: {created}[/dim]")
    except Exception:
        pass

    console.print()


def _add_entry(console: Console, db: Database, output_format: str):
    """Add a new journal entry"""
    console.print()
    console.print(Panel("[bold]New Journal Entry[/bold]", border_style="cyan"))
    console.print()

    # Title
    title = Prompt.ask("[cyan]Title[/cyan]")
    if not title:
        console.print("[yellow]Cancelled.[/yellow]")
        return

    # Type
    entry_type = Prompt.ask(
        "[cyan]Entry type[/cyan]",
        choices=["note", "win", "loss", "lesson"],
        default="note"
    )

    # Market ID (optional)
    market_id = Prompt.ask("[cyan]Market ID (optional)[/cyan]", default="")

    # Content
    console.print("[cyan]Content[/cyan] [dim](multi-line, end with empty line):[/dim]")
    lines = []
    while True:
        line = Prompt.ask("", default="")
        if not line and lines:
            break
        lines.append(line)

    content = '\n'.join(lines).strip()
    if not content:
        console.print("[yellow]No content entered. Cancelled.[/yellow]")
        return

    # Outcome (for win/loss)
    outcome = ""
    if entry_type in ['win', 'loss']:
        outcome = Prompt.ask("[cyan]Outcome/Result[/cyan]", default="")

    # Lesson
    lesson = ""
    if entry_type == 'lesson' or Confirm.ask("[cyan]Add a lesson learned?[/cyan]", default=False):
        lesson = Prompt.ask("[cyan]Lesson learned[/cyan]", default="")

    # Tags
    tags = Prompt.ask("[cyan]Tags (comma-separated)[/cyan]", default="")

    # Save
    now = datetime.now().isoformat()

    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO trade_journal
            (title, market_id, entry_type, content, tags, outcome, lesson, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (title, market_id, entry_type, content, tags, outcome, lesson, now, now))
        entry_id = cursor.lastrowid

    if output_format == 'json':
        print_json({'success': True, 'action': 'created', 'id': entry_id})
    else:
        console.print()
        console.print(f"[green]Journal entry #{entry_id} created![/green]")


def _delete_entry(console: Console, db: Database, entry_id: int, output_format: str):
    """Delete a journal entry"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trade_journal WHERE id = ?", (entry_id,))
        deleted = cursor.rowcount > 0

    if output_format == 'json':
        print_json({'success': deleted, 'deleted_id': entry_id if deleted else None})
    else:
        if deleted:
            console.print(f"[green]Entry #{entry_id} deleted.[/green]")
        else:
            console.print(f"[yellow]Entry #{entry_id} not found.[/yellow]")


def _search_entries(console: Console, db: Database, query: str, limit: int, output_format: str):
    """Search journal entries"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trade_journal
            WHERE title LIKE ? OR content LIKE ? OR tags LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f'%{query}%', f'%{query}%', f'%{query}%', limit))
        entries = [dict(row) for row in cursor.fetchall()]

    if output_format == 'json':
        print_json({'success': True, 'query': query, 'count': len(entries), 'entries': entries})
        return

    if not entries:
        console.print(f"[yellow]No entries matching '{query}'[/yellow]")
        return

    console.print()
    console.print(Panel(f"[bold]Search: {query}[/bold]", border_style="cyan"))
    console.print()

    for entry in entries:
        try:
            date = datetime.fromisoformat(entry['created_at']).strftime("%m/%d")
        except Exception:
            date = "?"

        console.print(f"  [cyan]#{entry['id']}[/cyan] [{date}] {entry['title']}")

    console.print()
    console.print(f"[dim]{len(entries)} results[/dim]")
    console.print()


def _filter_by_tag(console: Console, db: Database, tag: str, limit: int, output_format: str):
    """Filter entries by tag"""
    with db._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM trade_journal
            WHERE tags LIKE ?
            ORDER BY created_at DESC LIMIT ?
        """, (f'%{tag}%', limit))
        entries = [dict(row) for row in cursor.fetchall()]

    if output_format == 'json':
        print_json({'success': True, 'tag': tag, 'count': len(entries), 'entries': entries})
        return

    if not entries:
        console.print(f"[yellow]No entries with tag '{tag}'[/yellow]")
        return

    console.print()
    console.print(Panel(f"[bold]Tag: {tag}[/bold]", border_style="cyan"))
    console.print()

    for entry in entries:
        try:
            date = datetime.fromisoformat(entry['created_at']).strftime("%m/%d")
        except Exception:
            date = "?"

        entry_type = entry.get('entry_type', 'note')
        if entry_type == 'win':
            type_str = "[green]W[/green]"
        elif entry_type == 'loss':
            type_str = "[red]L[/red]"
        else:
            type_str = "[dim]-[/dim]"

        console.print(f"  [cyan]#{entry['id']}[/cyan] {type_str} [{date}] {entry['title']}")

    console.print()
    console.print(f"[dim]{len(entries)} entries[/dim]")
    console.print()
