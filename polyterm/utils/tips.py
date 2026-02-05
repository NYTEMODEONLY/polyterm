"""Tips and hints system for beginner guidance"""

import random
from typing import List, Optional
from pathlib import Path


# General tips shown throughout the app
GENERAL_TIPS = [
    "Price = Probability. A $0.65 price means the market thinks there's a 65% chance.",
    "Press 't' anytime to run the interactive tutorial.",
    "Press 'g' to see the glossary of prediction market terms.",
    "Use 'polyterm simulate -i' to calculate potential profit before trading.",
    "High volume usually means better liquidity and tighter spreads.",
    "Whales are traders with $100k+ volume. Their moves often signal information.",
    "Smart money = wallets with >70% win rate. Worth watching!",
    "Arbitrage = risk-free profit from price differences. Check daily!",
    "Set up alerts (option 12) to never miss important market moves.",
    "All commands support --format json for scripting and automation.",
]

# Tips specific to different screens/features
MONITOR_TIPS = [
    "Green prices are rising (more likely), red are falling (less likely).",
    "Sort by volume to find the most actively traded markets.",
    "Use --active-only to hide closed/resolved markets.",
    "High volume + big price change = something interesting happening.",
]

WHALE_TIPS = [
    "Whale activity often precedes significant price movements.",
    "Track specific whales with: polyterm wallets --follow <address>",
    "Smart money (high win rate) is often more informative than raw volume.",
    "Fresh wallets making large bets may indicate insider information.",
]

ARBITRAGE_TIPS = [
    "Intra-market arb: When YES + NO < $1.00, buy both for guaranteed profit.",
    "Cross-platform arb compares Polymarket vs Kalshi prices.",
    "Remember to account for fees (2% on Polymarket winnings).",
    "Arbitrage opportunities close fast - act quickly!",
]

PREDICT_TIPS = [
    "Predictions combine multiple signals: momentum, volume, whale activity, etc.",
    "Higher confidence doesn't always mean correct - it's one data point.",
    "Signals work best when multiple factors align (e.g., bullish momentum + whale buying).",
    "Check the order book for additional confirmation.",
]

ORDERBOOK_TIPS = [
    "Wide spread = low liquidity, your order may move the price.",
    "Use --slippage to calculate how much a large order would cost.",
    "Bid/ask imbalance can signal directional pressure.",
    "Iceberg orders hide large positions - detected by unusual patterns.",
]

ALERT_TIPS = [
    "Set up Telegram alerts for real-time notifications.",
    "Adjust thresholds in Settings to reduce noise.",
    "Unread alerts appear first - acknowledge them to clear the list.",
]

# Map of context to tips
CONTEXT_TIPS = {
    "monitor": MONITOR_TIPS,
    "whale": WHALE_TIPS,
    "whales": WHALE_TIPS,
    "arbitrage": ARBITRAGE_TIPS,
    "predict": PREDICT_TIPS,
    "prediction": PREDICT_TIPS,
    "orderbook": ORDERBOOK_TIPS,
    "order_book": ORDERBOOK_TIPS,
    "alert": ALERT_TIPS,
    "alerts": ALERT_TIPS,
}


def get_random_tip(context: Optional[str] = None) -> str:
    """Get a random tip, optionally context-specific

    Args:
        context: Optional context like 'monitor', 'whale', etc.

    Returns:
        A random tip string
    """
    if context and context.lower() in CONTEXT_TIPS:
        # 70% chance of context-specific tip, 30% general
        if random.random() < 0.7:
            return random.choice(CONTEXT_TIPS[context.lower()])

    return random.choice(GENERAL_TIPS)


def get_tips_for_context(context: str, count: int = 3) -> List[str]:
    """Get multiple tips for a specific context

    Args:
        context: Context like 'monitor', 'whale', etc.
        count: Number of tips to return

    Returns:
        List of tip strings
    """
    context_tips = CONTEXT_TIPS.get(context.lower(), [])
    all_tips = context_tips + GENERAL_TIPS

    # Shuffle and return requested count
    shuffled = all_tips.copy()
    random.shuffle(shuffled)
    return shuffled[:count]


def should_show_tip() -> bool:
    """Determine if we should show a tip (not too frequently)

    Shows tips ~30% of the time to avoid being annoying.
    """
    return random.random() < 0.3


def format_tip(tip: str) -> str:
    """Format a tip for display

    Args:
        tip: The tip text

    Returns:
        Formatted tip string for Rich console
    """
    return f"[dim]Tip: {tip}[/dim]"


class TipTracker:
    """Track which tips have been shown to avoid repetition"""

    def __init__(self):
        self.shown_tips = set()
        self.tip_file = Path.home() / ".polyterm" / ".shown_tips"

    def _load_shown(self):
        """Load previously shown tips"""
        try:
            if self.tip_file.exists():
                content = self.tip_file.read_text().strip()
                self.shown_tips = set(line for line in content.split('\n') if line)
        except Exception:
            pass

    def _save_shown(self):
        """Save shown tips"""
        try:
            self.tip_file.parent.mkdir(parents=True, exist_ok=True)
            self.tip_file.write_text('\n'.join(self.shown_tips))
        except Exception:
            pass

    def get_new_tip(self, context: Optional[str] = None) -> Optional[str]:
        """Get a tip that hasn't been shown recently

        Args:
            context: Optional context for tip selection

        Returns:
            A tip string or None if all tips have been shown
        """
        self._load_shown()

        # Get candidate tips
        if context and context.lower() in CONTEXT_TIPS:
            candidates = CONTEXT_TIPS[context.lower()] + GENERAL_TIPS
        else:
            candidates = GENERAL_TIPS

        # Filter out shown tips
        available = [t for t in candidates if t not in self.shown_tips]

        # If all shown, reset
        if not available:
            self.shown_tips.clear()
            available = candidates

        # Pick one
        tip = random.choice(available)
        self.shown_tips.add(tip)

        # Reset if too many tips tracked (preserve current tip)
        if len(self.shown_tips) > 20:
            self.shown_tips.clear()
            self.shown_tips.add(tip)

        self._save_shown()
        return tip


# Singleton tracker
_tracker = None


def get_tip_tracker() -> TipTracker:
    """Get the global tip tracker"""
    global _tracker
    if _tracker is None:
        _tracker = TipTracker()
    return _tracker
