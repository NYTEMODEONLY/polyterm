"""Contextual help system - Screen-specific help and hints"""

from rich.console import Console
from rich.panel import Panel
from rich.table import Table


# Contextual help content for each screen/feature
HELP_CONTENT = {
    "monitor": {
        "title": "Market Monitor Help",
        "description": "Real-time market tracking with live updates.",
        "usage": [
            ("--limit N", "Show N markets (default: 20)"),
            ("--category X", "Filter by category: politics, crypto, sports"),
            ("--sort X", "Sort by: volume, probability, recent"),
            ("--active-only", "Show only active, unclosed markets"),
            ("--once", "Run once without live updates"),
        ],
        "tips": [
            "Markets update every 5 seconds by default",
            "Press Ctrl+C to stop live monitoring",
            "Use --format json for scripting integration",
        ],
        "shortcuts": "m",
    },
    "whales": {
        "title": "Whale Tracking Help",
        "description": "Track high-volume market activity from large traders.",
        "usage": [
            ("--min-amount N", "Minimum trade size to track (default: $10,000)"),
            ("--hours N", "Hours of history to check (default: 24)"),
            ("--market ID", "Filter by specific market ID"),
            ("--limit N", "Maximum trades to show (default: 20)"),
        ],
        "tips": [
            "Whale trades often signal upcoming price movements",
            "Lower --min-amount to see more activity",
            "Combine with smart money wallets for better signals",
        ],
        "shortcuts": "w, 3",
    },
    "arbitrage": {
        "title": "Arbitrage Scanner Help",
        "description": "Find pricing inefficiencies across markets.",
        "usage": [
            ("--min-spread N", "Minimum spread percentage (default: 2.5%)"),
            ("--limit N", "Maximum opportunities to show (default: 10)"),
            ("--include-kalshi", "Include cross-platform (Kalshi) opportunities"),
        ],
        "tips": [
            "Intra-market: YES + NO prices should equal ~$1.00",
            "Correlated: Similar markets with different prices",
            "Higher spreads = higher profit but rarer",
            "Act fast - arbitrage windows close quickly",
        ],
        "shortcuts": "arb, 9",
    },
    "predict": {
        "title": "Predictions Help",
        "description": "Signal-based market predictions using multiple factors.",
        "usage": [
            ("--market ID", "Analyze a specific market"),
            ("--limit N", "Number of markets to analyze (default: 10)"),
            ("--horizon N", "Prediction horizon in hours (default: 24)"),
            ("--min-confidence N", "Minimum confidence threshold (default: 0.5)"),
        ],
        "tips": [
            "Predictions use momentum, volume, whale activity, and technicals",
            "Higher confidence = stronger consensus of signals",
            "+ direction = bullish, - direction = bearish",
            "Historical accuracy shown at bottom",
        ],
        "shortcuts": "pred, 10",
    },
    "risk": {
        "title": "Risk Assessment Help",
        "description": "Evaluate markets on 6 risk factors with A-F grades.",
        "usage": [
            ("--market X", "Market ID or search term to analyze"),
        ],
        "factors": [
            ("Resolution Clarity", "25%", "How objective is the resolution criteria?"),
            ("Liquidity", "20%", "How much capital is available to trade?"),
            ("Time Risk", "15%", "How far until resolution?"),
            ("Volume Quality", "15%", "Signs of wash trading or manipulation?"),
            ("Spread", "15%", "How wide is the bid-ask spread?"),
            ("Category Risk", "10%", "Historical reliability of category"),
        ],
        "tips": [
            "A-B grade markets are generally safer for beginners",
            "Check warnings section for specific concerns",
            "Follow recommendations to reduce risk",
        ],
        "shortcuts": "risk, 14",
    },
    "follow": {
        "title": "Copy Trading Help",
        "description": "Follow successful traders to learn from their moves.",
        "usage": [
            ("--list", "List all followed wallets"),
            ("--add ADDRESS", "Follow a new wallet"),
            ("--remove ADDRESS", "Stop following a wallet"),
        ],
        "tips": [
            "Maximum 10 followed wallets",
            "Find wallets with 'polyterm wallets --type smart'",
            "Check win rate and volume before following",
            "Set up alerts to get notified when followed wallets trade",
        ],
        "shortcuts": "follow, copy, 15",
    },
    "parlay": {
        "title": "Parlay Calculator Help",
        "description": "Combine multiple bets for higher potential payouts.",
        "usage": [
            ("--markets X", "Comma-separated probabilities (e.g., '0.65,0.70,0.80')"),
            ("--amount N", "Bet amount in USD (default: $100)"),
            ("-i", "Interactive mode (recommended)"),
        ],
        "tips": [
            "ALL legs must win for a parlay to pay out",
            "More legs = higher payout but lower probability",
            "Expected value shows if the bet is mathematically favorable",
            "Risk level: Moderate (25%+), High (10-25%), Very High (5-10%), Extreme (<5%)",
        ],
        "shortcuts": "parlay, 16",
    },
    "simulate": {
        "title": "Position Simulator Help",
        "description": "Calculate potential profit/loss before placing a trade.",
        "usage": [
            ("--shares N", "Number of shares to simulate"),
            ("--entry N", "Entry price (0.01-0.99)"),
            ("--probability N", "Your estimated outcome probability"),
            ("-i", "Interactive mode"),
        ],
        "tips": [
            "Always calculate your max loss before trading",
            "Consider fees (2% on winnings)",
            "Use conservative probability estimates",
        ],
        "shortcuts": "sim, simulate",
    },
    "wallets": {
        "title": "Wallet Tracking Help",
        "description": "Analyze and track smart money and whale wallets.",
        "usage": [
            ("--type X", "Type: smart (high win rate), whales (high volume), all"),
            ("--market ID", "Filter by market"),
            ("--min-volume N", "Minimum volume threshold"),
        ],
        "tips": [
            "Smart money = wallets with >55% win rate",
            "Whales = wallets with large average positions",
            "Use 'polyterm follow --add' to track specific wallets",
        ],
        "shortcuts": "wal, 11",
    },
    "alerts": {
        "title": "Alerts Help",
        "description": "Set up notifications for market events.",
        "usage": [
            ("--list", "Show all active alerts"),
            ("--add", "Add a new alert"),
            ("--remove ID", "Remove an alert"),
        ],
        "alert_types": [
            ("Price", "Trigger when market crosses price threshold"),
            ("Volume", "Trigger on unusual volume"),
            ("Whale", "Trigger on large trades"),
            ("Followed", "Trigger when followed wallets trade"),
        ],
        "tips": [
            "Desktop notifications work on macOS and Linux",
            "Email alerts require configuration in settings",
        ],
        "shortcuts": "alert, 12",
    },
}


def show_contextual_help(console: Console, screen_name: str):
    """Display contextual help for a specific screen"""
    help_data = HELP_CONTENT.get(screen_name)

    if not help_data:
        console.print(f"[yellow]No specific help available for '{screen_name}'[/yellow]")
        console.print("[dim]Press 'h' from the main menu for general help.[/dim]")
        return

    console.print()
    console.print(Panel(
        f"[bold]{help_data['title']}[/bold]\n\n"
        f"[dim]{help_data['description']}[/dim]",
        border_style="cyan",
    ))
    console.print()

    # Usage/options
    if "usage" in help_data:
        console.print("[bold yellow]Options[/bold yellow]")
        usage_table = Table(show_header=False, box=None, padding=(0, 2))
        usage_table.add_column(style="cyan", width=20)
        usage_table.add_column(style="white")
        for option, desc in help_data["usage"]:
            usage_table.add_row(option, desc)
        console.print(usage_table)
        console.print()

    # Risk factors (for risk command)
    if "factors" in help_data:
        console.print("[bold yellow]Risk Factors[/bold yellow]")
        factors_table = Table(show_header=True, box=None, padding=(0, 2))
        factors_table.add_column("Factor", style="cyan")
        factors_table.add_column("Weight", justify="center")
        factors_table.add_column("Description")
        for factor, weight, desc in help_data["factors"]:
            factors_table.add_row(factor, weight, desc)
        console.print(factors_table)
        console.print()

    # Alert types (for alerts command)
    if "alert_types" in help_data:
        console.print("[bold yellow]Alert Types[/bold yellow]")
        alert_table = Table(show_header=False, box=None, padding=(0, 2))
        alert_table.add_column(style="cyan", width=12)
        alert_table.add_column(style="white")
        for alert_type, desc in help_data["alert_types"]:
            alert_table.add_row(alert_type, desc)
        console.print(alert_table)
        console.print()

    # Tips
    if "tips" in help_data:
        console.print("[bold green]Tips[/bold green]")
        for tip in help_data["tips"]:
            console.print(f"  [green]+[/green] {tip}")
        console.print()

    # Keyboard shortcuts
    if "shortcuts" in help_data:
        console.print(f"[dim]Keyboard shortcuts: {help_data['shortcuts']}[/dim]")


def get_quick_tip(screen_name: str) -> str:
    """Get a single quick tip for a screen"""
    help_data = HELP_CONTENT.get(screen_name)
    if help_data and "tips" in help_data and help_data["tips"]:
        import random
        return random.choice(help_data["tips"])
    return ""
