# Contextual Help -- Screen-specific help content for the TUI

A data-driven help system that provides per-screen usage instructions, option tables, tips, and keyboard shortcuts, rendered as Rich Panels and Tables when the user presses `?` or `h` within a TUI screen.

## Overview

Each TUI screen in PolyTerm has a corresponding entry in the `HELP_CONTENT` dictionary. An entry contains the screen's title, a description, a list of CLI options with explanations, contextual tips, and the keyboard shortcut(s) that reach the screen. Some entries carry additional structured data -- the risk assessment screen lists its six weighted factors, and the alerts screen lists its alert types.

The `show_contextual_help()` function takes a screen name, looks it up in `HELP_CONTENT`, and renders a formatted help display using Rich Panels and Tables. If no help exists for the given screen, a fallback message directs the user to the main help menu. A companion function `get_quick_tip()` returns a single random tip for a screen, useful for inline hints that do not warrant a full help display.

## HELP_CONTENT Structure

Each entry in the `HELP_CONTENT` dictionary is itself a dictionary with these fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `title` | str | Yes | Displayed as the Panel header (e.g., "Market Monitor Help") |
| `description` | str | Yes | One-line description shown below the title |
| `usage` | list of (flag, description) tuples | Yes | CLI options rendered as a two-column table |
| `tips` | list of str | Yes | Contextual advice shown in green |
| `shortcuts` | str | Yes | TUI keyboard shortcuts (e.g., "m", "arb, 9") |
| `factors` | list of (name, weight, description) tuples | No | Risk factors with weights (risk screen only) |
| `alert_types` | list of (type, description) tuples | No | Alert type definitions (alerts screen only) |

## Covered Screens

| Screen Key | Title | Shortcuts |
|---|---|---|
| `monitor` | Market Monitor Help | `m` |
| `whales` | Whale Tracking Help | `w, 3` |
| `arbitrage` | Arbitrage Scanner Help | `arb, 9` |
| `predict` | Predictions Help | `pred, 10` |
| `risk` | Risk Assessment Help | `risk, 14` |
| `follow` | Copy Trading Help | `follow, copy, 15` |
| `parlay` | Parlay Calculator Help | `parlay, 16` |
| `simulate` | Position Simulator Help | `sim, simulate` |
| `wallets` | Wallet Tracking Help | `wal, 11` |
| `alerts` | Alerts Help | `alert, 12` |

### Screen Details

**monitor** -- Options for `--limit`, `--category`, `--sort`, `--active-only`, `--once`. Tips cover update frequency, Ctrl+C to stop, and JSON output.

**whales** -- Options for `--min-amount`, `--hours`, `--market`, `--limit`. Tips cover whale-price correlation, lowering thresholds, and smart money combination.

**arbitrage** -- Options for `--min-spread`, `--limit`, `--include-kalshi`. Tips explain intra-market, correlated, and cross-platform arbitrage types, plus the importance of speed.

**predict** -- Options for `--market`, `--limit`, `--horizon`, `--min-confidence`. Tips cover multi-signal methodology, confidence interpretation, and directional notation.

**risk** -- Options for `--market`. Includes a `factors` table with six weighted risk dimensions: Resolution Clarity (25%), Liquidity (20%), Time Risk (15%), Volume Quality (15%), Spread (15%), Category Risk (10%). Tips advise beginners to start with A-B grades.

**follow** -- Options for `--list`, `--add`, `--remove`. Tips cover the 10-wallet limit, finding wallets, and alert integration.

**parlay** -- Options for `--markets`, `--amount`, `-i`. Tips explain all-legs-must-win mechanics, expected value, and risk level thresholds (Moderate 25%+, High 10-25%, Very High 5-10%, Extreme <5%).

**simulate** -- Options for `--shares`, `--entry`, `--probability`, `-i`. Tips advise calculating max loss, considering fees, and using conservative estimates.

**wallets** -- Options for `--type` (smart/whales/all), `--market`, `--min-volume`. Tips clarify smart money and whale definitions.

**alerts** -- Options for `--list`, `--add`, `--remove`. Includes an `alert_types` table: Price, Volume, Whale, Followed. Tips cover desktop notification support and email configuration.

## Key Functions

### `show_contextual_help(console, screen_name)`

Renders the full help display for `screen_name`. Output structure:

1. A cyan-bordered Rich Panel with the title and description.
2. An "Options" section with a two-column table of flags and descriptions.
3. A "Risk Factors" section (risk screen only) with a three-column table of factor, weight, and description.
4. An "Alert Types" section (alerts screen only) with a two-column table.
5. A "Tips" section with green bullet points.
6. A dim line showing keyboard shortcuts.

If `screen_name` is not found in `HELP_CONTENT`, prints a yellow message directing the user to the main help menu.

```python
from polyterm.utils.contextual_help import show_contextual_help

show_contextual_help(console, "arbitrage")
```

### `get_quick_tip(screen_name)`

Returns a single random tip string for the given screen, or an empty string if no help content exists. Useful for showing a one-liner at the bottom of a screen without rendering the full help panel.

```python
from polyterm.utils.contextual_help import get_quick_tip

tip = get_quick_tip("monitor")
if tip:
    console.print(f"[dim]{tip}[/dim]")
```

## Usage Examples

**In a TUI screen, respond to the `?` key:**

```python
from polyterm.utils.contextual_help import show_contextual_help

class MonitorScreen:
    def handle_input(self, key):
        if key == "?":
            show_contextual_help(self.console, "monitor")
            return
        # ... handle other keys ...
```

**Show a quick tip after rendering content:**

```python
from polyterm.utils.contextual_help import get_quick_tip

# After main display
tip = get_quick_tip("whales")
if tip:
    console.print(f"\n[dim]Tip: {tip}[/dim]")
```

**Check if help exists before offering it:**

```python
from polyterm.utils.contextual_help import HELP_CONTENT

if screen_name in HELP_CONTENT:
    console.print("[dim]Press ? for help[/dim]")
```

## Related Features

- **Tips system** (`utils/tips.py`) -- provides a parallel randomized tip system with session-aware non-repetition via `TipTracker`. The contextual help tips are static per screen; the tips module adds randomization and cross-session tracking.
- **Tutorial command** (`cli/commands/tutorial.py`) -- the interactive tutorial walks through features in depth, while contextual help provides quick reference.
- **TUI controller** (`tui/controller.py`) -- routes `?` and `h` keypresses to `show_contextual_help()` for the active screen.
- **Glossary command** (`cli/commands/glossary.py`) -- defines prediction market terminology, complementing the how-to-use focus of contextual help.

Source: `polyterm/utils/contextual_help.py`
