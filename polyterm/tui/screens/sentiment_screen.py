"""TUI Screen for Market Sentiment Analysis"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_sentiment_screen(console: Console):
    """Market sentiment analysis screen"""
    console.print()
    console.print(Panel("[bold]Market Sentiment Analysis[/bold]", border_style="cyan"))
    console.print()
    console.print("[bold]Analyze sentiment from multiple market signals[/bold]")
    console.print()
    console.print("[dim]Combines momentum, volume, orderbook, trades, and whale activity[/dim]")
    console.print()

    search = Prompt.ask("[cyan]Search for market[/cyan]", default="")

    if search:
        console.print()
        subprocess.run([sys.executable, "-m", "polyterm.cli.main", "sentiment", "--market", search])
