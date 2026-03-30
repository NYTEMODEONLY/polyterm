"""Price Alert Screen - Set price alerts"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from ...utils.errors import handle_api_error


def run_pricealert_screen(console: Console):
    """Launch price alert command in interactive mode"""
    console.print(Panel(
        "[bold]Price Alerts[/bold]\n\n"
        "[dim]Set alerts to notify you when markets hit target prices.[/dim]",
        title="[cyan]Price Alerts[/cyan]",
        border_style="cyan",
    ))
    console.print()

    try:
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "pricealert", "-i"])
    except Exception as e:
        handle_api_error(console, e, "price alerts")
