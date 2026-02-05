"""Parlay calculator TUI screen"""

import subprocess
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt


def run_parlay_screen(console: Console):
    """Interactive parlay calculator screen"""
    console.clear()
    console.print(Panel(
        "[bold]Parlay Calculator[/bold]\n\n"
        "[dim]Combine multiple bets for higher potential payouts.[/dim]\n\n"
        "[yellow]What is a parlay?[/yellow]\n"
        "A parlay combines multiple bets into one. ALL legs must win\n"
        "for you to profit. The more legs, the higher the potential\n"
        "payout - but lower chance of winning.\n\n"
        "Options:\n"
        "  [cyan]1.[/cyan] Interactive mode (recommended)\n"
        "  [cyan]2.[/cyan] Quick calculation\n\n"
        "[dim]2-10 legs supported per parlay.[/dim]",
        title="[cyan]Parlay Calculator[/cyan]",
        border_style="cyan",
    ))
    console.print()

    choice = Prompt.ask(
        "[cyan]Select option[/cyan]",
        choices=["1", "2", "q"],
        default="1"
    )

    if choice == "q":
        return

    if choice == "1":
        # Interactive mode
        cmd = [sys.executable, "-m", "polyterm.cli.main", "parlay", "-i"]
    else:
        # Quick calculation
        console.print()
        console.print("[dim]Enter probabilities as comma-separated decimals or percentages.[/dim]")
        console.print("[dim]Example: 0.65,0.70,0.80 or 65,70,80[/dim]")
        console.print()

        markets = Prompt.ask("[cyan]Enter probabilities[/cyan]")
        if not markets:
            console.print("[yellow]No probabilities entered.[/yellow]")
            Prompt.ask("[dim]Press Enter to return to menu[/dim]")
            return

        # Normalize input (convert percentages to decimals)
        try:
            probs = []
            for p in markets.split(','):
                val = float(p.strip())
                if val > 1:
                    val = val / 100
                probs.append(str(val))
            markets = ','.join(probs)
        except ValueError:
            console.print("[red]Invalid probability format.[/red]")
            Prompt.ask("[dim]Press Enter to return to menu[/dim]")
            return

        amount = Prompt.ask("[cyan]Bet amount ($)[/cyan]", default="100")

        try:
            amount = float(amount)
        except ValueError:
            amount = 100.0

        cmd = [sys.executable, "-m", "polyterm.cli.main", "parlay", "--markets", markets, "--amount", str(amount)]

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
