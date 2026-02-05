"""Orderbook Screen - Order book analysis and visualization"""

import subprocess
from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table

from .market_picker import pick_market, get_market_id, get_market_title


def orderbook_screen(console: RichConsole):
    """Analyze order book for a market

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Order Book Analyzer[/bold]\n[dim]Depth charts, slippage, liquidity analysis[/dim]", style="cyan"))
    console.print()

    # Ask user how they want to select a market
    console.print("[bold]Select Market:[/bold]")
    console.print()

    menu = Table.grid(padding=(0, 1))
    menu.add_column(style="cyan bold", justify="right", width=3)
    menu.add_column(style="white")

    menu.add_row("1", "Choose from List - Select from active markets")
    menu.add_row("2", "Enter Token ID - Manual token ID entry")
    menu.add_row("", "")
    menu.add_row("b", "Back - Return to main menu")

    console.print(menu)
    console.print()

    choice = console.input("[cyan]Select option (1-2, b):[/cyan] ").strip().lower()
    console.print()

    market_id = None

    if choice == '1':
        # Pick from list
        market = pick_market(
            console,
            prompt="Select a market for order book analysis",
            allow_manual=True,
            limit=15,
        )
        if not market:
            console.print("[yellow]No market selected[/yellow]")
            return

        # For order book, we need the token ID, not the event ID
        # The token ID is typically in 'clobTokenIds' or similar
        clob_ids = market.get('clobTokenIds', [])
        if isinstance(clob_ids, str):
            try:
                import json
                clob_ids = json.loads(clob_ids)
            except Exception:
                clob_ids = []

        if clob_ids:
            # Show YES/NO choice if multiple tokens
            if len(clob_ids) >= 2:
                console.print()
                console.print("[bold]Select outcome:[/bold]")
                console.print("  [cyan]1[/cyan] YES token")
                console.print("  [cyan]2[/cyan] NO token")
                outcome = console.input("[cyan]Choice (1/2):[/cyan] ").strip()
                if outcome == '2' and len(clob_ids) > 1:
                    market_id = clob_ids[1]
                else:
                    market_id = clob_ids[0]
            else:
                market_id = clob_ids[0]
        else:
            # Fall back to regular ID
            market_id = get_market_id(market)

        if not market_id:
            console.print("[red]Could not get token ID for this market[/red]")
            console.print("[dim]Try entering the token ID manually[/dim]")
            market_id = console.input("[cyan]Enter token ID:[/cyan] ").strip()
            if not market_id:
                return

    elif choice == '2':
        # Manual ID entry
        market_id = console.input(
            "[cyan]Enter market token ID:[/cyan] "
        ).strip()
        if not market_id:
            console.print("[red]No ID provided[/red]")
            return

    elif choice == 'b':
        return

    else:
        console.print("[red]Invalid option[/red]")
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
        "Show ASCII depth chart? [cyan](y/n)[/cyan] [default: y] "
    ).strip().lower()
    show_chart = show_chart != 'n'

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
