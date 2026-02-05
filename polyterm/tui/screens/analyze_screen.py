"""TUI Screen for Portfolio Analytics"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel


def run_analyze_screen(console: Console):
    """Portfolio analytics screen"""
    console.print()
    console.print(Panel("[bold]Portfolio Analytics[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Analyze your portfolio exposure and risk[/bold]")
    console.print()
    console.print("[dim]Shows category exposure, concentration risk,[/dim]")
    console.print("[dim]and recommendations for portfolio balance.[/dim]")
    console.print()

    subprocess.run([sys.executable, "-m", "polyterm.cli.main", "analyze"])
