"""News TUI Screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_news_screen(console: Console):
    """Display news aggregation screen"""
    console.print()
    console.print(Panel(
        "[bold cyan]Market News[/bold cyan]\n\n"
        "Latest headlines from crypto and prediction market sources.\n"
        "[dim]Sources: The Block, CoinDesk, Decrypt[/dim]",
        border_style="cyan"
    ))
    console.print()

    console.print("[bold]Options:[/bold]")
    console.print("  [cyan]1[/cyan] - Latest news (24h)")
    console.print("  [cyan]2[/cyan] - Breaking news (6h)")
    console.print("  [cyan]3[/cyan] - News for a market")
    console.print("  [cyan]b[/cyan] - Back to menu")
    console.print()

    choice = Prompt.ask("[cyan]Choice[/cyan]", choices=["1", "2", "3", "b"], default="1")

    if choice == "b":
        return

    if choice == "1":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "news"]
    elif choice == "2":
        cmd = [sys.executable, "-m", "polyterm.cli.main", "news", "--hours", "6"]
    elif choice == "3":
        market = Prompt.ask("[cyan]Market search term[/cyan]")
        if not market:
            return
        cmd = [sys.executable, "-m", "polyterm.cli.main", "news", "--market", market]

    console.print()

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Returned to menu[/yellow]")
