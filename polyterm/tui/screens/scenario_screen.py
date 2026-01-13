"""TUI Screen for Scenario Analysis"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_scenario_screen(console: Console):
    """Scenario analysis screen"""
    console.print()
    console.print(Panel("[bold]Scenario Analysis[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Model what-if outcomes for your positions[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Analyze portfolio (all positions)")
    console.print("  [yellow]2.[/yellow] Analyze specific market")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        console.print()
        subprocess.run(["polyterm", "scenario", "--portfolio"])

    elif choice == "2":
        console.print()
        market = Prompt.ask("[cyan]Enter market name[/cyan]")
        if market:
            subprocess.run(["polyterm", "scenario", "--market", market])
