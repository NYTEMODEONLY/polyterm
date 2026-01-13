"""TUI Screen for Probability Calibration"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_calibrate_screen(console: Console):
    """Probability calibration screen"""
    console.print()
    console.print(Panel("[bold]Probability Calibration[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Track how accurate your probability estimates are[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] View calibration stats")
    console.print("  [yellow]2.[/yellow] Log a new prediction")
    console.print("  [yellow]3.[/yellow] Resolve a prediction")
    console.print("  [yellow]4.[/yellow] List all predictions")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "1":
        subprocess.run(["polyterm", "calibrate", "--stats"])

    elif choice == "2":
        subprocess.run(["polyterm", "calibrate", "--add"])

    elif choice == "3":
        subprocess.run(["polyterm", "calibrate", "--resolve"])

    elif choice == "4":
        subprocess.run(["polyterm", "calibrate", "--list"])
