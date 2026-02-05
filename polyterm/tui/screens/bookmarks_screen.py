"""Bookmarks TUI screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_bookmarks_screen(console: Console):
    """Interactive bookmarks screen"""
    console.clear()
    console.print(Panel(
        "[bold]Market Bookmarks[/bold]\n\n"
        "[dim]Save and manage your favorite markets.[/dim]\n\n"
        "Options:\n"
        "  [cyan]1.[/cyan] View bookmarks\n"
        "  [cyan]2.[/cyan] Add a bookmark\n"
        "  [cyan]3.[/cyan] Interactive mode (full features)\n",
        title="[cyan]Bookmarks[/cyan]",
        border_style="cyan",
    ))
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "q"],
        default="1"
    )

    if choice == "q":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "bookmarks", "--list"]
    elif choice == "2":
        console.print()
        search = Prompt.ask("[cyan]Enter market name to bookmark[/cyan]")
        if not search:
            console.print("[yellow]No market specified.[/yellow]")
            Prompt.ask("[dim]Press Enter to return to menu[/dim]")
            return
        cmd = [sys.executable, "-m", "polyterm.cli.main", "bookmarks", "--add", search]
    else:
        cmd = [sys.executable, "-m", "polyterm.cli.main", "bookmarks"]

    console.print()
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    console.print()

    try:
        subprocess.run(cmd, capture_output=False)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    console.print()
    Prompt.ask("[dim]Press Enter to return to menu[/dim]")
