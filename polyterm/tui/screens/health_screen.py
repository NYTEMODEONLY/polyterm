"""TUI Screen for Portfolio Health"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_health_screen(console: Console):
    """Portfolio health screen"""
    console.print()
    console.print(Panel("[bold]Portfolio Health Check[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Comprehensive portfolio health analysis[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] Quick health check")
    console.print("  [yellow]2.[/yellow] Detailed analysis")
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
        subprocess.run(["polyterm", "health"])

    elif choice == "2":
        console.print()
        subprocess.run(["polyterm", "health", "--detailed"])
