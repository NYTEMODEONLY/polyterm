"""Dashboard TUI screen"""

import subprocess
import sys
from rich.console import Console
from rich.prompt import Prompt


def run_dashboard_screen(console: Console):
    """Quick dashboard overview screen"""
    console.clear()

    cmd = [sys.executable, "-m", "polyterm.cli.main", "dashboard"]

    try:
        subprocess.run(cmd, capture_output=False)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    console.print()
    Prompt.ask("[dim]Press Enter to return to menu[/dim]")
