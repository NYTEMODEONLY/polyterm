"""Predictions Screen - Signal-based market predictions"""

import subprocess
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table

from .market_picker import pick_market, get_market_id, get_market_title


def predictions_screen(console: RichConsole):
    """Generate signal-based predictions for markets

    Uses momentum, volume, whale activity, and technical indicators.
    No external AI/LLM required - all analysis is algorithmic.

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Signal-Based Predictions[/bold]\n[dim]Momentum, volume, whale & technical analysis[/dim]", style="cyan"))
    console.print()

    # Ask user what they want to do
    console.print("[bold]Prediction Options:[/bold]")
    console.print()

    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")

    menu.add_row("1", "Analyze Top Markets - Predictions for highest volume markets")
    menu.add_row("2", "Select Specific Market - Choose from list")
    menu.add_row("3", "Enter Market ID - Manual ID entry")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-3):[/cyan] ").strip()
    console.print()

    market_id = None
    limit = 10

    if choice == '1':
        # Top markets - ask for limit
        limit_input = console.input(
            "How many markets to analyze? [cyan][default: 10][/cyan] "
        ).strip() or "10"
        try:
            limit = int(limit_input)
            if limit < 1:
                limit = 10
            elif limit > 25:
                limit = 25
        except ValueError:
            limit = 10

    elif choice == '2':
        # Pick from list
        market = pick_market(
            console,
            prompt="Select a market for prediction",
            allow_manual=True,
            limit=15,
        )
        if not market:
            console.print("[yellow]No market selected[/yellow]")
            return
        market_id = get_market_id(market)
        if not market_id:
            console.print("[red]Could not get market ID[/red]")
            return

    elif choice == '3':
        # Manual ID entry
        market_id = console.input(
            "[cyan]Enter market ID or slug:[/cyan] "
        ).strip()
        if not market_id:
            console.print("[red]No ID provided[/red]")
            return

    else:
        console.print("[red]Invalid option[/red]")
        return

    # Get prediction settings
    console.print()
    console.print("[bold]Prediction Settings:[/bold]")

    # Prediction horizon
    horizon = console.input(
        "Prediction horizon in hours [cyan][default: 24][/cyan] "
    ).strip() or "24"
    try:
        horizon = int(horizon)
        if horizon < 1:
            horizon = 24
        elif horizon > 168:  # max 1 week
            horizon = 168
    except ValueError:
        horizon = 24

    # Minimum confidence
    min_confidence = console.input(
        "Minimum confidence (0-1) [cyan][default: 0.5][/cyan] "
    ).strip() or "0.5"
    try:
        min_confidence = float(min_confidence)
        if min_confidence < 0 or min_confidence > 1:
            min_confidence = 0.5
    except ValueError:
        min_confidence = 0.5

    console.print()
    console.print(f"[green]Generating predictions (horizon: {horizon}h)...[/green]")
    console.print()

    # Build and run command
    cmd = [
        "polyterm", "predict",
        f"--horizon={horizon}",
        f"--min-confidence={min_confidence}"
    ]
    if market_id:
        cmd.extend([f"--market={market_id}"])
    else:
        cmd.extend([f"--limit={limit}"])

    try:
        result = subprocess.run(cmd, capture_output=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Prediction cancelled.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
