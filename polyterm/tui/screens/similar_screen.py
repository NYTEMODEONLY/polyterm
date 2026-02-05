"""TUI Screen for Similar Markets"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_similar_screen(console: Console):
    """Similar markets screen"""
    console.print()
    console.print(Panel("[bold]Similar Markets[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Find markets related to one you're watching[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Enter a market to find similar[/cyan]")

    if not market:
        return

    console.print()
    console.print("[cyan]Match type:[/cyan]")
    console.print("  [yellow]1.[/yellow] All (topic + category)")
    console.print("  [yellow]2.[/yellow] Topic only")
    console.print("  [yellow]3.[/yellow] Category only")
    console.print()

    match_type = Prompt.ask(
        "[cyan]Select match type[/cyan]",
        choices=["1", "2", "3"],
        default="1"
    )

    type_map = {"1": "all", "2": "topic", "3": "category"}
    selected_type = type_map.get(match_type, "all")

    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "similar", market, "--type", selected_type])
