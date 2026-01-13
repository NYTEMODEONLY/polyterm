"""Risk assessment TUI screen"""

import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_risk_screen(console: Console):
    """Interactive risk assessment screen"""
    console.clear()
    console.print(Panel(
        "[bold]Market Risk Assessment[/bold]\n\n"
        "[dim]Evaluate markets on 6 risk factors:[/dim]\n"
        "  - Resolution clarity (subjective vs objective)\n"
        "  - Liquidity quality\n"
        "  - Time to resolution\n"
        "  - Volume patterns (wash trading indicators)\n"
        "  - Spread\n"
        "  - Category risk\n\n"
        "[dim]Each market receives a grade (A-F) based on weighted scores.[/dim]",
        title="[cyan]Risk Assessment[/cyan]",
        border_style="cyan",
    ))
    console.print()

    # Get market input
    market = Prompt.ask(
        "[cyan]Enter market ID or search term[/cyan]",
        default=""
    )

    if not market:
        console.print("[yellow]No market specified.[/yellow]")
        Prompt.ask("[dim]Press Enter to return to menu[/dim]")
        return

    # Build command
    cmd = ["polyterm", "risk", "--market", market]

    console.print()
    console.print(f"[dim]Running: {' '.join(cmd)}[/dim]")
    console.print()

    # Run command
    try:
        result = subprocess.run(cmd, capture_output=False)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")

    console.print()
    Prompt.ask("[dim]Press Enter to return to menu[/dim]")
