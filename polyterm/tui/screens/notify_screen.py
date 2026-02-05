"""TUI Screen for Notification Settings"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_notify_screen(console: Console):
    """Notification settings screen"""
    console.print()
    console.print(Panel("[bold]Notification Settings[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Configure how you receive alerts[/bold]")
    console.print()
    console.print("[cyan]Options:[/cyan]")
    console.print("  [yellow]1.[/yellow] View current settings")
    console.print("  [yellow]2.[/yellow] Interactive configuration")
    console.print("  [yellow]3.[/yellow] Test notifications")
    console.print("  [yellow]4.[/yellow] Enable/disable desktop")
    console.print("  [yellow]5.[/yellow] Enable/disable sound")
    console.print("  [yellow]6.[/yellow] Configure webhook")
    console.print("  [yellow]b.[/yellow] Back to menu")
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "3", "4", "5", "6", "b"],
        default="1"
    )

    if choice == "b":
        return

    console.print()

    if choice == "1":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--status"])

    elif choice == "2":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--configure"])

    elif choice == "3":
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--test"])

    elif choice == "4":
        action = Prompt.ask("[cyan]Enable or disable?[/cyan]", choices=["enable", "disable"])
        if action == "enable":
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--enable", "desktop"])
        else:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--disable", "desktop"])

    elif choice == "5":
        action = Prompt.ask("[cyan]Enable or disable?[/cyan]", choices=["enable", "disable"])
        if action == "enable":
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--enable", "sound"])
        else:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--disable", "sound"])

    elif choice == "6":
        url = Prompt.ask("[cyan]Webhook URL[/cyan]")
        if url:
            subprocess.run([sys.executable, "-m", "polyterm.cli.main", "notify", "--webhook", url])
