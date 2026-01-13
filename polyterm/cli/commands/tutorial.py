"""Interactive tutorial for new users"""

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
import time


TUTORIAL_STEPS = [
    {
        "title": "Welcome to PolyTerm!",
        "content": """
**PolyTerm** is a terminal-based monitoring tool for prediction markets like Polymarket and Kalshi.

**What are prediction markets?**
- Markets where you buy/sell shares based on event outcomes
- Prices reflect the crowd's probability estimate
- If you're right, you profit. If wrong, you lose your stake.

**Why PolyTerm?**
- Real-time market monitoring
- Whale & insider tracking
- Arbitrage opportunity detection
- No browser needed - fast & lightweight

Press Enter to continue...
""",
    },
    {
        "title": "Understanding Prices = Probability",
        "content": """
**The most important concept:**

In prediction markets, **price = probability**.

| Price | Meaning |
|-------|---------|
| $0.75 | Market thinks 75% chance of YES |
| $0.25 | Market thinks 25% chance of YES |
| $0.50 | Market is uncertain (50/50) |

**Example:**
- "Will it rain tomorrow?" trading at $0.30
- The market thinks there's a 30% chance of rain
- If it rains, YES shares pay $1.00 (you profit $0.70)
- If it doesn't, your $0.30 is lost

**Key insight:** Find markets where you disagree with the price!

Press Enter to continue...
""",
    },
    {
        "title": "Your First Market Monitor",
        "content": """
Let's see live market data!

**The Monitor screen shows:**
- Market question/title
- Current probability (YES price)
- 24-hour volume (how much has been traded)
- Recent price change

**Reading the display:**
- [green]Green[/green] = price going up (more likely)
- [red]Red[/red] = price going down (less likely)
- High volume = active market with good liquidity

Press Enter to see a live market demonstration...
""",
    },
    {
        "title": "Whale Tracking",
        "content": """
**What is a whale?**
A trader with large positions (typically $100,000+).

**Why track whales?**
- They often have better information
- Large trades can move markets
- Following smart money can be profitable

**PolyTerm detects:**
- High-volume markets (whale activity)
- Smart money (wallets with >70% win rate)
- Suspicious patterns (potential insider trading)

**Commands:**
- `polyterm whales` - See high-volume markets
- `polyterm wallets --type whales` - Track whale wallets
- `polyterm wallets --type smart` - Find smart money

Press Enter to continue...
""",
    },
    {
        "title": "Arbitrage Opportunities",
        "content": """
**What is arbitrage?**
Risk-free profit from price differences.

**Types PolyTerm detects:**

1. **Intra-market**: YES + NO prices < $1.00
   - Buy both sides, guarantee profit
   - Example: YES=$0.48, NO=$0.49 = $0.03 profit

2. **Correlated markets**: Similar events, different prices
   - Same outcome priced differently
   - Buy low, sell high

3. **Cross-platform**: Polymarket vs Kalshi
   - Same event, different platforms
   - Price differences = opportunity

**Command:** `polyterm arbitrage`

Press Enter to continue...
""",
    },
    {
        "title": "Predictions & Signals",
        "content": """
**PolyTerm generates predictions using multiple signals:**

| Signal | What it measures |
|--------|------------------|
| Momentum | Price trend direction |
| Volume | Trading activity increase |
| Whale | Large wallet positioning |
| Smart Money | High win-rate wallet activity |
| Order Book | Buy/sell pressure imbalance |
| Technical | RSI and moving averages |

**Reading predictions:**
- Confidence: How strong the signal (0-100%)
- Direction: Bullish (up), Bearish (down), Neutral

**Command:** `polyterm predict`

Press Enter to continue...
""",
    },
    {
        "title": "Setting Up Alerts",
        "content": """
**Never miss important events!**

**PolyTerm can alert you via:**
- Telegram (recommended)
- Discord webhooks
- System notifications
- Email (SMTP)
- Sound alerts

**Alert types:**
- Whale activity detected
- Insider pattern flagged
- Arbitrage opportunity found
- Market price shifts significantly

**Setup:**
1. Run `polyterm` and go to Settings (8)
2. Configure your notification channels
3. Set your thresholds

**Test:** `polyterm alerts --test-telegram`

Press Enter to continue...
""",
    },
    {
        "title": "Quick Reference",
        "content": """
**TUI Shortcuts:**
| Key | Action |
|-----|--------|
| 1-13 | Navigate to feature |
| h or ? | Help screen |
| q | Quit |
| u | Quick update |

**Essential CLI commands:**
```
polyterm                    # Launch TUI
polyterm monitor --limit 10 # Quick market check
polyterm whales --hours 24  # Whale activity
polyterm arbitrage          # Find arbitrage
polyterm predict            # Get predictions
polyterm alerts             # View alerts
```

**Getting help:**
- Press ? in TUI for contextual help
- Run `polyterm <command> --help`
- Run `polyterm glossary` for terms

Press Enter to complete the tutorial...
""",
    },
]


@click.command()
@click.option("--step", default=0, help="Start from specific step (0-indexed)")
@click.option("--quick", is_flag=True, help="Quick mode - no pauses")
def tutorial(step, quick):
    """Interactive tutorial for new users

    Learn how prediction markets work and how to use PolyTerm effectively.
    """
    console = Console()

    console.clear()

    # Header
    console.print(Panel(
        "[bold cyan]PolyTerm Interactive Tutorial[/bold cyan]\n"
        "[dim]Learn prediction markets in 5 minutes[/dim]",
        border_style="cyan"
    ))
    console.print()

    total_steps = len(TUTORIAL_STEPS)

    for i, tutorial_step in enumerate(TUTORIAL_STEPS[step:], start=step + 1):
        # Progress indicator
        console.print(f"[dim]Step {i} of {total_steps}[/dim]")
        console.print()

        # Title
        console.print(f"[bold yellow]{tutorial_step['title']}[/bold yellow]")
        console.print()

        # Content (render as markdown for formatting)
        console.print(Markdown(tutorial_step['content']))

        # Demo for step 3 (market monitor)
        if i == 3 and not quick:
            _demo_market_monitor(console)

        if not quick:
            try:
                input()
            except (KeyboardInterrupt, EOFError):
                console.print("\n[yellow]Tutorial interrupted.[/yellow]")
                return

        console.clear()

    # Completion
    _show_completion(console)


def _demo_market_monitor(console: Console):
    """Show a brief demo of market data"""
    console.print()
    console.print("[cyan]Fetching sample market data...[/cyan]")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        progress.add_task("Loading markets...", total=None)
        time.sleep(1.5)

    # Sample data display
    table = Table(title="Sample Market Data", show_header=True)
    table.add_column("Market", style="white", max_width=35)
    table.add_column("Prob", justify="right", style="cyan")
    table.add_column("Volume", justify="right", style="yellow")
    table.add_column("Change", justify="right")

    # Sample markets
    markets = [
        ("Will BTC reach $100k in 2025?", "67%", "$2.1M", "[green]+5%[/green]"),
        ("Fed rate cut in March?", "34%", "$890K", "[red]-3%[/red]"),
        ("Rain in NYC tomorrow?", "45%", "$12K", "[dim]+0%[/dim]"),
    ]

    for m in markets:
        table.add_row(*m)

    console.print(table)
    console.print()


def _show_completion(console: Console):
    """Show completion message"""
    console.print(Panel(
        "[bold green]Tutorial Complete![/bold green]\n\n"
        "You now know the basics of:\n"
        "  - How prediction markets work\n"
        "  - Reading prices as probabilities\n"
        "  - Tracking whales and smart money\n"
        "  - Finding arbitrage opportunities\n"
        "  - Using PolyTerm's features\n\n"
        "[cyan]Next steps:[/cyan]\n"
        "  1. Run [bold]polyterm[/bold] to explore the TUI\n"
        "  2. Check [bold]polyterm glossary[/bold] for terms\n"
        "  3. Set up alerts in Settings (8)\n\n"
        "[dim]Happy trading![/dim]",
        border_style="green",
        title="Congratulations!"
    ))
    console.print()

    # Mark tutorial as completed
    try:
        from pathlib import Path
        onboarded_file = Path.home() / ".polyterm" / ".onboarded"
        onboarded_file.parent.mkdir(parents=True, exist_ok=True)
        onboarded_file.touch()
    except Exception:
        pass
