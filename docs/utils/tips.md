# Tips -- Context-aware tips and hints for beginner guidance

A lightweight system that surfaces helpful tips throughout the application, with context-specific advice weighted toward the feature the user is currently using.

## Overview

PolyTerm displays tips at roughly 30% frequency to help new users learn the tool without overwhelming experienced ones. Tips are organized into context-specific lists (monitor, whale tracking, arbitrage, predictions, order book, alerts) plus a general pool. When a tip is requested with a context, there is a 70% chance of drawing from the context-specific list and a 30% chance of drawing from the general pool.

A `TipTracker` class persists which tips have already been shown in `~/.polyterm/.shown_tips`, so the system avoids repeating the same tip until all available tips for a context have been displayed. The tracker resets automatically when its internal set exceeds 20 entries or when all candidates have been exhausted.

## Tip Lists

### `GENERAL_TIPS` (10 tips)

Broad advice applicable anywhere in the application. Examples:

- "Price = Probability. A $0.65 price means the market thinks there's a 65% chance."
- "All commands support --format json for scripting and automation."
- "Arbitrage = risk-free profit from price differences. Check daily!"
- "Smart money = wallets with >70% win rate. Worth watching!"

### Context-Specific Tips

| List | Count | Covers |
|---|---|---|
| `MONITOR_TIPS` | 4 | Color meaning, sorting by volume, active-only filter, volume+change signals |
| `WHALE_TIPS` | 4 | Price movement correlation, wallet following, smart money vs volume, fresh wallet risk |
| `ARBITRAGE_TIPS` | 4 | Intra-market mechanics, cross-platform comparison, fee accounting, speed urgency |
| `PREDICT_TIPS` | 4 | Multi-signal approach, confidence caveats, signal alignment, order book confirmation |
| `ORDERBOOK_TIPS` | 4 | Spread/liquidity relationship, slippage calculation, bid/ask imbalance, iceberg detection |
| `ALERT_TIPS` | 3 | Telegram setup, threshold tuning, unread alert management |

### `CONTEXT_TIPS` Mapping

Maps context strings to their tip lists. Supports aliases so both `"whale"` and `"whales"` resolve to `WHALE_TIPS`, and both `"orderbook"` and `"order_book"` resolve to `ORDERBOOK_TIPS`.

```python
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
```

## Key Functions

### `get_random_tip(context=None)`

Returns a single random tip string. When `context` is provided and matches a key in `CONTEXT_TIPS`, there is a 70% probability of returning a context-specific tip. Otherwise returns a general tip.

```python
get_random_tip()              # Random general tip
get_random_tip("arbitrage")   # 70% arbitrage tip, 30% general tip
```

### `get_tips_for_context(context, count=3)`

Returns up to `count` tips for the given context. Combines the context-specific list with `GENERAL_TIPS`, shuffles, and returns the first `count` entries. Useful for help screens that display multiple tips at once.

```python
tips = get_tips_for_context("monitor", count=2)
# ["Green prices are rising...", "Press 't' anytime to run..."]
```

### `should_show_tip()`

Returns `True` approximately 30% of the time. Used as a gate to avoid showing tips on every screen transition.

```python
if should_show_tip():
    console.print(format_tip(get_random_tip("whale")))
```

### `format_tip(tip)`

Wraps the tip text in Rich dim markup for display: `"[dim]Tip: {tip}[/dim]"`.

## TipTracker Class

The `TipTracker` maintains a set of previously shown tips to avoid repetition within a session and across sessions.

**`__init__()`** -- Initializes with an empty `shown_tips` set. The persistence file is `~/.polyterm/.shown_tips`.

**`get_new_tip(context=None)`** -- Returns a tip that has not been shown recently. Loads the shown-tips file, filters candidates, picks a random unshown tip, saves the updated set. If all tips have been shown, the set is cleared and the cycle restarts. The set is also cleared if it exceeds 20 entries to prevent unbounded growth.

**`_load_shown()` / `_save_shown()`** -- File I/O for the shown-tips persistence. Both silently catch exceptions so that file permission issues never break the application.

### Singleton Access

```python
from polyterm.utils.tips import get_tip_tracker

tracker = get_tip_tracker()  # Returns the global TipTracker instance
tip = tracker.get_new_tip("monitor")
```

The module-level `_tracker` variable holds the singleton, initialized on first call to `get_tip_tracker()`.

## Usage Examples

**Show a tip after a screen loads:**

```python
from polyterm.utils.tips import should_show_tip, get_random_tip, format_tip

# After displaying main content
if should_show_tip():
    console.print(format_tip(get_random_tip("arbitrage")))
```

**Use TipTracker for non-repeating tips across sessions:**

```python
from polyterm.utils.tips import get_tip_tracker

tracker = get_tip_tracker()
tip = tracker.get_new_tip("whale")
if tip:
    console.print(f"[dim]Tip: {tip}[/dim]")
```

**Display multiple tips on a help screen:**

```python
from polyterm.utils.tips import get_tips_for_context

console.print("[bold]Tips:[/bold]")
for tip in get_tips_for_context("predict", count=3):
    console.print(f"  [green]+[/green] {tip}")
```

## Related Features

- **Contextual help** (`utils/contextual_help.py`) -- the help system embeds its own per-screen tips in `HELP_CONTENT`; the tips module provides the randomized, non-repeating variant.
- **Tutorial command** (`cli/commands/tutorial.py`) -- the interactive tutorial references many of the same concepts covered in tips.
- **Error formatting** (`utils/errors.py`) -- `format_suggestion()` uses the same `[dim]Tip: ...[/dim]` pattern for visual consistency.
- **TUI screens** (`tui/screens/`) -- screens call `should_show_tip()` and `get_random_tip()` to display contextual hints after rendering content.

Source: `polyterm/utils/tips.py`
