"""TUI Screen for Price Ladder"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_ladder_screen(console: Console):
    """Price ladder screen"""
    console.print()
    console.print(Panel("[bold]Price Ladder[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Visual order book depth at each price level[/bold]")
    console.print()

    market = Prompt.ask("[cyan]Enter market to view ladder[/cyan]")

    if not market:
        return

    console.print()
    console.print("[cyan]Which side?[/cyan]")
    console.print("  [yellow]1.[/yellow] Both YES and NO")
    console.print("  [yellow]2.[/yellow] YES only")
    console.print("  [yellow]3.[/yellow] NO only")
    console.print()

    side_choice = Prompt.ask(
        "[cyan]Select side[/cyan]",
        choices=["1", "2", "3"],
        default="1"
    )

    side_map = {"1": "both", "2": "yes", "3": "no"}
    selected_side = side_map.get(side_choice, "both")

    console.print()
    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "ladder", market, "--side", selected_side])
