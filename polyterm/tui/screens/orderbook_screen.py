"""Orderbook Screen - Order book analysis and visualization"""

import subprocess
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table


def orderbook_screen(console: RichConsole):
    """Analyze order book for a market

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Order Book Analyzer[/bold]", style="cyan"))
    console.print()

    # Get market ID (required)
    market_id = console.input(
        "[cyan]Enter market token ID:[/cyan] "
    ).strip()
    if not market_id:
        console.print("[red]Market ID is required[/red]")
        return

    console.print()
    console.print("[bold]Analysis Options:[/bold]")
    console.print()

    # Depth
    depth = console.input(
        "Order book depth [cyan][default: 20][/cyan] "
    ).strip() or "20"
    try:
        depth = int(depth)
        if depth < 1:
            depth = 20
        elif depth > 100:
            depth = 100
    except ValueError:
        depth = 20

    # Show chart
    show_chart = console.input(
        "Show ASCII depth chart? [cyan](y/n)[/cyan] [default: n] "
    ).strip().lower()
    show_chart = show_chart == 'y'

    # Slippage calculation
    slippage_size = console.input(
        "Calculate slippage for order size (shares)? [cyan][leave blank to skip][/cyan] "
    ).strip()
    slippage = None
    slippage_side = "buy"
    if slippage_size:
        try:
            slippage = float(slippage_size)
            slippage_side = console.input(
                "Order side [cyan](buy/sell)[/cyan] [default: buy] "
            ).strip().lower() or "buy"
            if slippage_side not in ['buy', 'sell']:
                slippage_side = 'buy'
        except ValueError:
            slippage = None

    console.print()
    console.print("[green]Analyzing order book...[/green]")
    console.print()

    # Build and run command
    cmd = ["polyterm", "orderbook", market_id, f"--depth={depth}"]
    if show_chart:
        cmd.append("--chart")
    if slippage:
        cmd.extend([f"--slippage={slippage}", f"--side={slippage_side}"])

    try:
        result = subprocess.run(cmd, capture_output=False)
    except KeyboardInterrupt:
        console.print("\n[yellow]Analysis cancelled.[/yellow]")
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
