"""TUI Screen for Screener Presets"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_presets_screen(console: Console):
    """Screener presets management screen"""
    console.print()
    console.print(Panel("[bold]Screener Presets[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Save and reuse search filter combinations[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] List saved presets")
    console.print("  [yellow]2.[/yellow] Create new preset")
    console.print("  [yellow]3.[/yellow] Run a preset")
    console.print("  [yellow]4.[/yellow] View preset details")
    console.print("  [yellow]5.[/yellow] Delete a preset")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "5", "b"],
        default="1"
    )

    if choice == "b":
        return

    if choice == "1":
        # List presets
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "presets", "--list"])

    elif choice == "2":
        # Create preset interactively
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "presets", "--interactive"])

    elif choice == "3":
        # Run preset
        console.print()
        name = Prompt.ask("[cyan]Preset name to run[/cyan]", default="")
        if name:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "presets", "--run", name])

    elif choice == "4":
        # View preset
        console.print()
        name = Prompt.ask("[cyan]Preset name to view[/cyan]", default="")
        if name:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "presets", "--view", name])

    elif choice == "5":
        # Delete preset
        console.print()
        name = Prompt.ask("[cyan]Preset name to delete[/cyan]", default="")
        if name:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "presets", "--delete", name])
