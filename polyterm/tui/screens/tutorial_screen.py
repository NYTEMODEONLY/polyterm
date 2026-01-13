"""Tutorial Screen - Interactive tutorial for new users"""

import subprocess
import sys
from rich.console import Console as RichConsole
from rich.panel import Panel
from rich.prompt import Confirm


def tutorial_screen(console: RichConsole):
    """Launch interactive tutorial

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Interactive Tutorial[/bold]", style="cyan"))
    console.print()

    console.print("[cyan]The tutorial will teach you:[/cyan]")
    console.print("  - How prediction markets work")
    console.print("  - Understanding prices as probabilities")
    console.print("  - Tracking whales and smart money")
    console.print("  - Finding arbitrage opportunities")
    console.print("  - Using PolyTerm's features")
    console.print()

    if Confirm.ask("[cyan]Start the tutorial?[/cyan]", default=True):
        console.print()
        console.print("[dim]Starting tutorial...[/dim]")
        console.print()

        # Run the tutorial command
        try:
            subprocess.run([sys.executable, "-m", "polyterm", "tutorial"])
        except Exception as e:
            console.print(f"[red]Error running tutorial: {e}[/red]")
            console.print("[dim]Try running: polyterm tutorial[/dim]")
    else:
        console.print("[yellow]Tutorial cancelled.[/yellow]")
        console.print("[dim]You can run it later with: polyterm tutorial[/dim]")
