"""Wallet Cluster Detection TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_clusters_screen(console: Console):
    """Display wallet cluster detection screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]Wallet Cluster Detection[/bold cyan]\n\n"
        "Detect wallets controlled by the same entity.\n"
        "[dim]Analyzes timing, market overlap, and trade sizes.[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Detect clusters (default)")
    console.print("  [cyan]2[/cyan] - Custom minimum score")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "b"], default="1")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "clusters"]
    elif choice == "2":
        score = Prompt.ask("[cyan]Min score (0-100)[/cyan]", default="60")
        cmd = [sys.executable, "-m", "polyterm.cli.main", "clusters", "--min-score", score]

    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
