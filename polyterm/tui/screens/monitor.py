"""Monitor Screen - Real-time market tracking"""

from rich.panel import Panel
from rich.console import Console as RichConsole
from rich.table import Table
import subprocess
import sys


# Category options with descriptions
CATEGORY_OPTIONS = [
    ("all", "🌐 All Markets", "Show all active markets"),
    ("sports", "🏈 Sports", "NFL, NBA, Super Bowl, Soccer, Golf..."),
    ("crypto", "💰 Crypto", "Bitcoin, Ethereum, Solana, XRP..."),
    ("politics", "🏛️ Politics", "Elections, Trump, Congress..."),
]

# Sub-categories for drilling down
SPORTS_SUBCATEGORIES = [
    ("sports", "🏈 All Sports", "All sports markets"),
    ("nfl", "🏈 NFL", "NFL games, Super Bowl, playoffs"),
    ("nba", "🏀 NBA", "NBA games, championships"),
    ("mlb", "⚾ MLB", "Baseball, World Series"),
    ("nhl", "🏒 NHL", "Hockey, Stanley Cup"),
    ("soccer", "⚽ Soccer", "Premier League, World Cup, FIFA"),
    ("golf", "⛳ Golf", "PGA, Masters, tournaments"),
    ("tennis", "🎾 Tennis", "Grand Slams, ATP, WTA"),
    ("ufc", "🥊 UFC/Boxing", "MMA, boxing matches"),
    ("f1", "🏎️ F1/Racing", "Formula 1, NASCAR"),
]

CRYPTO_SUBCATEGORIES = [
    ("crypto", "💰 All Crypto", "All crypto markets"),
    ("bitcoin", "₿ Bitcoin", "BTC price, ETFs"),
    ("ethereum", "⟠ Ethereum", "ETH price, upgrades"),
    ("solana", "◎ Solana", "SOL price"),
    ("altcoins", "🪙 Altcoins", "XRP, other tokens"),
]

POLITICS_SUBCATEGORIES = [
    ("politics", "🏛️ All Politics", "All political markets"),
    ("trump", "🇺🇸 Trump", "Trump-related markets"),
    ("elections", "🗳️ Elections", "Election predictions"),
    ("congress", "🏛️ Congress", "Senate, House votes"),
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

    category = None
    subcategories = None

    try:
        cat_idx = int(cat_choice) - 1
        if 0 <= cat_idx < len(CATEGORY_OPTIONS):
            main_category = CATEGORY_OPTIONS[cat_idx][0]

            # Check for sub-categories
            if main_category == "sports":
                subcategories = SPORTS_SUBCATEGORIES
            elif main_category == "crypto":
                subcategories = CRYPTO_SUBCATEGORIES
            elif main_category == "politics":
                subcategories = POLITICS_SUBCATEGORIES

            if subcategories:
                # Show sub-category selection
                console.print()
                console.print(f"[cyan]Select specific {main_category}:[/cyan]")
                console.print()

                sub_table = Table(show_header=False, box=None, padding=(0, 2))
                sub_table.add_column("#", style="cyan", width=3)
                sub_table.add_column("Type", style="bold", width=18)
                sub_table.add_column("Examples", style="dim")

                for i, (key, name, desc) in enumerate(subcategories, 1):
                    sub_table.add_row(str(i), name, desc)

                console.print(sub_table)
                console.print()

                sub_choice = console.input(f"Select type [cyan][1-{len(subcategories)}, default: 1][/cyan] ").strip() or "1"

                try:
                    sub_idx = int(sub_choice) - 1
                    if 0 <= sub_idx < len(subcategories):
                        category = subcategories[sub_idx][0]
                        cat_name = subcategories[sub_idx][1]
                    else:
                        category = main_category
                        cat_name = main_category
                except ValueError:
                    category = main_category
                    cat_name = main_category
            elif main_category == "all":
                category = None
                cat_name = "All markets"
            else:
                category = main_category
                cat_name = main_category
    except ValueError:
        category = None
        cat_name = "All markets"

    if category:
        console.print(f"[green]Selected:[/green] {cat_name}")
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


