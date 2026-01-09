"""Predictions Screen - AI-powered market predictions"""

import subprocess
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table


def predictions_screen(console: RichConsole):
    """Generate AI-powered predictions for markets

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]AI Predictions[/bold]", style="cyan"))
    console.print()

    # Settings submenu
    console.print("[bold]Prediction Settings:[/bold]")
    console.print()

    # Specific market or top markets
    market_id = console.input(
        "Specific market ID [cyan][leave blank for top markets][/cyan] "
    ).strip()

    # If no specific market, ask for limit
    if not market_id:
        limit = console.input(
            "Number of markets to analyze [cyan][default: 10][/cyan] "
        ).strip() or "10"
        try:
            limit = int(limit)
            if limit < 1:
                limit = 10
            elif limit > 25:
                limit = 25
        except ValueError:
            limit = 10
    else:
        limit = 1

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
        "Minimum confidence [cyan][default: 0.5][/cyan] "
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
