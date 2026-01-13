"""Glossary of prediction market terms"""

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel


GLOSSARY = {
    # Core Concepts
    "prediction market": {
        "definition": "A market where participants buy and sell shares based on the probability of future events.",
        "example": "'Will Team X win the championship?' - Buy YES if you think they will.",
        "category": "Core Concepts",
    },
    "probability": {
        "definition": "The likelihood of an event occurring, expressed as a percentage (0-100%) or decimal (0-1).",
        "example": "A price of $0.65 means the market estimates 65% probability.",
        "category": "Core Concepts",
    },
    "binary market": {
        "definition": "A market with only two outcomes: YES or NO. Most Polymarket markets are binary.",
        "example": "'Will it rain tomorrow?' resolves to YES ($1) or NO ($0).",
        "category": "Core Concepts",
    },
    "resolution": {
        "definition": "The final determination of a market's outcome. Winners receive $1 per share.",
        "example": "The market resolves to YES, all YES shareholders get paid.",
        "category": "Core Concepts",
    },

    # Trading Terms
    "bid": {
        "definition": "The highest price a buyer is willing to pay for a share.",
        "example": "Bid at $0.45 means someone will buy at 45 cents.",
        "category": "Trading",
    },
    "ask": {
        "definition": "The lowest price a seller is willing to accept for a share.",
        "example": "Ask at $0.48 means someone will sell at 48 cents.",
        "category": "Trading",
    },
    "spread": {
        "definition": "The difference between the bid and ask prices. Lower spread = better liquidity.",
        "example": "Bid $0.45, Ask $0.48 = $0.03 spread (3%).",
        "category": "Trading",
    },
    "liquidity": {
        "definition": "How easily you can buy/sell without significantly moving the price.",
        "example": "High liquidity: Large orders fill at expected price.",
        "category": "Trading",
    },
    "slippage": {
        "definition": "The difference between expected price and actual execution price due to order size.",
        "example": "Wanted $0.50, got $0.52 average = $0.02 slippage.",
        "category": "Trading",
    },
    "order book": {
        "definition": "A list of all buy and sell orders at different price levels.",
        "example": "Order book shows $10K buying at $0.45, $15K selling at $0.48.",
        "category": "Trading",
    },

    # Market Analysis
    "whale": {
        "definition": "A trader with very large positions, typically $100,000+ in volume.",
        "example": "A whale just bought $500K of YES shares.",
        "category": "Analysis",
    },
    "smart money": {
        "definition": "Traders with consistently high win rates (70%+), suggesting superior information or skill.",
        "example": "Smart money is accumulating YES positions.",
        "category": "Analysis",
    },
    "insider": {
        "definition": "Someone trading on non-public information. Detected by suspicious timing patterns.",
        "example": "Fresh wallet makes $50K bet hours before news breaks.",
        "category": "Analysis",
    },
    "volume": {
        "definition": "Total value of shares traded in a given period (usually 24 hours).",
        "example": "$2.5M volume means $2.5 million was traded today.",
        "category": "Analysis",
    },
    "momentum": {
        "definition": "The rate and direction of price change over time.",
        "example": "Strong bullish momentum: price rose 10% in 6 hours.",
        "category": "Analysis",
    },

    # Arbitrage
    "arbitrage": {
        "definition": "Risk-free profit from price differences between markets or platforms.",
        "example": "YES + NO = $0.97, buy both for guaranteed $0.03 profit.",
        "category": "Arbitrage",
    },
    "intra-market arbitrage": {
        "definition": "Arbitrage within a single market when YES + NO < $1.00.",
        "example": "YES=$0.48, NO=$0.49, total=$0.97, profit=$0.03.",
        "category": "Arbitrage",
    },
    "cross-platform arbitrage": {
        "definition": "Arbitrage between different platforms (Polymarket vs Kalshi).",
        "example": "Polymarket YES=$0.60, Kalshi YES=$0.55, buy Kalshi.",
        "category": "Arbitrage",
    },

    # Platform Terms
    "polymarket": {
        "definition": "A decentralized prediction market platform built on Polygon blockchain.",
        "example": "Trade on polymarket.com using USDC.",
        "category": "Platforms",
    },
    "kalshi": {
        "definition": "A CFTC-regulated prediction market platform for US traders.",
        "example": "Kalshi offers regulated event contracts.",
        "category": "Platforms",
    },
    "uma": {
        "definition": "Universal Market Access - the oracle system Polymarket uses for dispute resolution.",
        "example": "UMA token holders vote on disputed market outcomes.",
        "category": "Platforms",
    },
    "usdc": {
        "definition": "USD Coin - a stablecoin pegged to $1 USD, used for Polymarket trading.",
        "example": "Deposit USDC to start trading on Polymarket.",
        "category": "Platforms",
    },
    "polygon": {
        "definition": "The blockchain network Polymarket runs on. Offers fast, cheap transactions.",
        "example": "Gas fees on Polygon are typically < $0.01.",
        "category": "Platforms",
    },

    # Technical Analysis
    "rsi": {
        "definition": "Relative Strength Index - measures overbought (>70) or oversold (<30) conditions.",
        "example": "RSI of 85 suggests the market may be overbought.",
        "category": "Technical",
    },
    "support": {
        "definition": "A price level where buying pressure tends to prevent further decline.",
        "example": "Strong support at $0.40 - price bounced there 3 times.",
        "category": "Technical",
    },
    "resistance": {
        "definition": "A price level where selling pressure tends to prevent further rise.",
        "example": "Resistance at $0.60 - price rejected there twice.",
        "category": "Technical",
    },
    "iceberg order": {
        "definition": "A large order split into smaller visible portions to hide true size.",
        "example": "Detected iceberg: only $5K visible but $50K total.",
        "category": "Technical",
    },

    # Risk Terms
    "risk score": {
        "definition": "PolyTerm's 0-100 rating of suspicious activity for a wallet.",
        "example": "Risk score 85 = high likelihood of insider trading.",
        "category": "Risk",
    },
    "wash trading": {
        "definition": "Fake trading where the same entity buys and sells to inflate volume.",
        "example": "Estimated 25% of Polymarket volume is wash trading.",
        "category": "Risk",
    },
    "dispute": {
        "definition": "A challenge to a market's resolution, decided by UMA token holders.",
        "example": "The market resolution was disputed and went to UMA vote.",
        "category": "Risk",
    },
}


@click.command()
@click.option("--search", "-s", default=None, help="Search for a specific term")
@click.option("--category", "-c", default=None, help="Filter by category")
@click.option("--list-categories", is_flag=True, help="List all categories")
def glossary(search, category, list_categories):
    """Prediction market glossary

    Learn the terminology used in prediction markets and PolyTerm.

    Examples:
        polyterm glossary                    # View all terms
        polyterm glossary --search whale     # Search for "whale"
        polyterm glossary --category Trading # View trading terms
    """
    console = Console()

    # List categories
    if list_categories:
        categories = sorted(set(term["category"] for term in GLOSSARY.values()))
        console.print(Panel("[bold]Available Categories[/bold]", style="cyan"))
        for cat in categories:
            count = sum(1 for t in GLOSSARY.values() if t["category"] == cat)
            console.print(f"  [cyan]{cat}[/cyan] ({count} terms)")
        return

    # Filter terms
    filtered_terms = GLOSSARY.copy()

    if search:
        search_lower = search.lower()
        filtered_terms = {
            k: v for k, v in GLOSSARY.items()
            if search_lower in k.lower() or search_lower in v["definition"].lower()
        }

    if category:
        category_lower = category.lower()
        filtered_terms = {
            k: v for k, v in filtered_terms.items()
            if v["category"].lower() == category_lower
        }

    if not filtered_terms:
        console.print(f"[yellow]No terms found matching your criteria.[/yellow]")
        console.print("[dim]Try: polyterm glossary --list-categories[/dim]")
        return

    # Group by category
    by_category = {}
    for term, data in sorted(filtered_terms.items()):
        cat = data["category"]
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append((term, data))

    # Display
    console.print(Panel(
        "[bold]Prediction Market Glossary[/bold]",
        subtitle=f"[dim]{len(filtered_terms)} terms[/dim]",
        style="cyan"
    ))
    console.print()

    for cat in sorted(by_category.keys()):
        console.print(f"[bold yellow]{cat}[/bold yellow]")
        console.print()

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Term", style="cyan bold", width=22)
        table.add_column("Definition", style="white")

        for term, data in by_category[cat]:
            table.add_row(term.title(), data["definition"])

        console.print(table)
        console.print()

    # Show example usage hint
    if not search and not category:
        console.print("[dim]Tip: Use --search <term> to find specific terms[/dim]")
        console.print("[dim]     Use --category <name> to filter by category[/dim]")
