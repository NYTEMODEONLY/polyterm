"""Monitor Screen - Real-time market tracking"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
import subprocess
import sys


# Category options with descriptions
CATEGORY_OPTIONS = [
    ("all", "🌐 All Markets", "Show all active markets"),
    ("sports", "🏈 Sports", "NFL, NBA, Super Bowl, Championships, Soccer..."),
    ("crypto", "💰 Crypto", "Bitcoin, Ethereum, Solana, XRP, DeFi..."),
    ("politics", "🏛️ Politics", "Elections, Trump, Biden, Congress, Senate..."),
]


def monitor_screen(console: RichConsole):
    """Interactive monitor screen with guided setup

    Args:
        console: Rich Console instance
    """
    console.print(Panel("[bold]Real-Time Market Monitor[/bold]", style="cyan"))
    console.print()

    # Get parameters interactively
    console.print("[dim]Configure your market monitor:[/dim]")
    console.print()

    limit = console.input("How many markets to display? [cyan][default: 20][/cyan] ").strip() or "20"

    # Category selection menu
    console.print()
    console.print("[cyan]Select category:[/cyan]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("#", style="cyan", width=3)
    table.add_column("Category", style="bold", width=15)
    table.add_column("Examples", style="dim")

    for i, (key, name, desc) in enumerate(CATEGORY_OPTIONS, 1):
        table.add_row(str(i), name, desc)

    console.print(table)
    console.print()

    cat_choice = console.input("Select category [cyan][1-4, default: 1][/cyan] ").strip() or "1"

    try:
        cat_idx = int(cat_choice) - 1
        if 0 <= cat_idx < len(CATEGORY_OPTIONS):
            category = CATEGORY_OPTIONS[cat_idx][0]
            if category == "all":
                category = None
        else:
            category = None
    except ValueError:
        category = None

    if category:
        console.print(f"[green]Selected:[/green] {category}")
    else:
        console.print("[green]Selected:[/green] All markets")

    console.print()
    refresh = console.input("Refresh rate in seconds? [cyan][default: 5][/cyan] ").strip() or "5"
    active_only = console.input("Active markets only? [cyan][Y/n][/cyan] ").strip().lower() != 'n'
    
    console.print()
    console.print("[green]Starting monitor...[/green]")
    console.print("[dim]Press Ctrl+C to stop[/dim]")
    console.print()
    
    # Build command
    cmd = [
        sys.executable, "-m", "polyterm.cli.main", "monitor",
        "--limit", limit,
        "--refresh", refresh,
    ]
    
    if category:
        cmd.extend(["--category", category])
    
    if active_only:
        cmd.append("--active-only")
    
    # Launch monitor command
    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        console.print("\n[yellow]Monitor stopped[/yellow]")


