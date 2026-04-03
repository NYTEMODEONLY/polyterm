# Formatting -- Terminal output formatting utilities

Pure functions for converting raw numeric and timestamp data into human-readable strings and Rich Text objects suitable for terminal display.

## Overview

This module contains stateless formatting functions used across CLI commands and TUI screens. It handles probability percentages with change indicators, volume abbreviations (K/M/B), Unix timestamp conversion, duration formatting, market title truncation, directional arrows, and ASCII volatility bars. The functions are designed to be lightweight and have no side effects, making them straightforward to test and compose.

Two variants exist for probability formatting: a plain-string version for general use and a Rich Text version that applies color coding based on the magnitude and direction of change.

## Key Functions

### `format_probability(probability, previous=None)`

Converts a numeric probability to a percentage string. When `previous` is provided, appends a signed change indicator if the absolute change is at least 0.1%.

```python
format_probability(65.3)             # "65.3%"
format_probability(65.3, 60.0)       # "65.3% (+5.3%)"
format_probability(42.1, 45.0)       # "42.1% (-2.9%)"
format_probability(50.0, 50.0)       # "50.0%"  (no change shown)
```

### `format_probability_rich(probability, previous=None)`

Returns a `rich.text.Text` object with color coding based on the direction and size of the change relative to `previous`:

| Change | Color |
|---|---|
| > +5% | `bright_green` |
| > 0% | `green` |
| < -5% | `bright_red` |
| < 0% | `red` |
| 0 or no previous | `white` |

The change indicator suffix (e.g., `(+5.3%)`) is rendered in the same color but dimmed. This function is used in Rich Tables and Live displays where color conveys information at a glance.

```python
text = format_probability_rich(72.0, 65.0)
# Rich Text: "72.0%" in bright_green + " (+7.0%)" in dim bright_green
```

### `format_volume(volume, use_short=True)`

Formats a numeric volume with K (thousands), M (millions), or B (billions) suffixes. When `use_short` is `False`, returns the full comma-separated number instead.

```python
format_volume(1_234_567)              # "1.23M"
format_volume(1_234_567, False)       # "1,234,567"
format_volume(500)                    # "500.00"
format_volume(45_000)                 # "45.00K"
format_volume(2_500_000_000)          # "2.50B"
```

### `format_timestamp(timestamp, include_time=True)`

Converts a Unix timestamp (integer seconds since epoch) to a human-readable string. When `include_time` is `False`, only the date portion is returned.

```python
format_timestamp(1700000000)          # "2023-11-14 22:13:20"
format_timestamp(1700000000, False)   # "2023-11-14"
```

### `format_duration(seconds)`

Converts an integer number of seconds into the most appropriate single-unit human-readable string.

| Range | Output |
|---|---|
| < 60 seconds | `"{n}s"` |
| < 3600 seconds | `"{n}m"` (integer minutes) |
| < 86400 seconds | `"{n}h"` (integer hours) |
| >= 86400 seconds | `"{n}d"` (integer days) |

```python
format_duration(45)      # "45s"
format_duration(300)     # "5m"
format_duration(7200)    # "2h"
format_duration(172800)  # "2d"
```

### `format_market_title(title, max_length=60)`

Truncates a market title to `max_length` characters, appending `"..."` if truncation occurs. Returns the original title unchanged if it fits.

```python
format_market_title("Will Bitcoin reach $100k by end of 2025?")
# "Will Bitcoin reach $100k by end of 2025?" (fits in 60 chars)

format_market_title("A very long market question that exceeds the limit", max_length=30)
# "A very long market question ..."
```

### `format_change_indicator(change)`

Returns a Unicode arrow indicating the direction of a numeric change.

```python
format_change_indicator(5.2)    # "↑"
format_change_indicator(-3.1)   # "↓"
format_change_indicator(0.0)    # "→"
```

### `create_volatility_bar(volatility, width=10)`

Generates an ASCII bar using block characters to visualize volatility on a 0-100 scale. Filled segments use `"█"` and empty segments use `"░"`.

```python
create_volatility_bar(50)       # "█████░░░░░"
create_volatility_bar(80, 20)   # "████████████████░░░░"
create_volatility_bar(0)        # "░░░░░░░░░░"
```

## Usage Examples

**In a Rich Table for market monitoring:**

```python
from polyterm.utils.formatting import format_probability_rich, format_volume

table.add_row(
    market["title"],
    format_probability_rich(current_prob, previous_prob),
    format_volume(market["volume24hr"]),
)
```

**In a CLI command for whale trades:**

```python
from polyterm.utils.formatting import format_timestamp, format_volume

for trade in whale_trades:
    print(f"{format_timestamp(trade['timestamp'])} | "
          f"${format_volume(trade['size'])} | "
          f"{format_change_indicator(trade['price_impact'])}")
```

**Truncating titles for compact display:**

```python
from polyterm.utils.formatting import format_market_title

for market in markets:
    console.print(format_market_title(market["title"], max_length=40))
```

## Related Features

- **Monitor command** (`cli/commands/monitor.py`) -- uses `format_probability_rich()` and `format_volume()` for the live market table.
- **Charts module** (`core/charts.py`) -- uses `create_volatility_bar()` style block characters for ASCII visualizations.
- **JSON output** (`utils/json_output.py`) -- when `--format json` is used, raw numeric values are emitted instead of formatted strings.
- **Dashboard** (`cli/commands/dashboard.py`) -- uses `format_volume()` for the quick overview display.

Source: `polyterm/utils/formatting.py`
