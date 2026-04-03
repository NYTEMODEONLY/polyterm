# Errors -- Centralized error handling with user-friendly messages

The error module provides a structured exception hierarchy and Rich-formatted display functions that turn raw exceptions into helpful, actionable messages for terminal users.

## Overview

Rather than letting Python tracebacks or opaque API errors reach the user, PolyTerm routes all error display through this module. It defines four exception subclasses of a common `PolyTermError` base, each carrying a human-readable `message`, an optional `suggestion`, and optional `details`. Display functions render these as Rich Panels with color-coded borders, while pattern-matching helper functions translate common API failures (timeouts, rate limits, 404s, 500s) into specific guidance.

The module also contains `ERROR_MESSAGES`, a dictionary of predefined error scenarios (no markets found, invalid wallet, database error, etc.) that any command can reference by key through `show_error()`.

## Key Classes

### `PolyTermError(Exception)`

Base exception class. All PolyTerm-specific exceptions inherit from this.

```python
PolyTermError(message: str, suggestion: str = None, details: str = None)
```

- `message` -- What went wrong, displayed in red.
- `suggestion` -- How to fix it, displayed in yellow.
- `details` -- Technical details, displayed dimmed.

### Subclasses

| Class | Purpose |
|---|---|
| `APIError` | Failures from Gamma, CLOB, Kalshi, or Data API calls |
| `ConfigError` | Problems loading or parsing `config.toml` |
| `ValidationError` | Invalid user input (bad market IDs, out-of-range values) |
| `NetworkError` | Connection-level failures (DNS, socket, TLS) |

All four subclasses inherit the same constructor signature and add no extra fields. The separation enables callers to catch specific error categories when needed.

## Key Functions

### `display_error(console, title, message, suggestion=None, details=None)`

Renders an error as a Rich Panel with a red border. The `title` appears as the panel header in bold red. The body contains the `message` in red, optional `details` in dim text, and an optional `suggestion` in yellow. Two blank lines are printed around the panel for visual separation.

```python
display_error(
    console,
    "Connection Timeout",
    "The API request took too long to respond.",
    suggestion="Check your internet connection or try again.",
    details="HTTPSConnectionPool: Read timed out."
)
```

### `handle_api_error(console, error, context="API request")`

Pattern-matches `str(error).lower()` against common failure signatures and calls `display_error()` with a tailored message:

| Pattern | Title | Suggestion |
|---|---|---|
| `timeout`, `timed out` | Connection Timeout | Check your internet connection or try again |
| `connection`, `connect` | Connection Failed | Check internet; Polymarket API may be down |
| `404`, `not found` | Not Found | Check market ID or search term |
| `403`, `forbidden`, `unauthorized` | Access Denied | Check API key in settings |
| `429`, `rate limit` | Rate Limited | Wait a few seconds before retrying |
| `500`, `internal server` | Server Error | Usually temporary; try again in a few minutes |
| (fallback) | API Error | Try again or check `polyterm --help` |

### `handle_validation_error(console, field, value, expected)`

Displays an "Invalid Input" panel explaining that `value` is not valid for `field`, with the `expected` format as the suggestion.

### `handle_config_error(console, error)`

Displays a "Configuration Error" panel suggesting the user run `polyterm config` or delete `~/.polyterm/config.toml` to reset.

### `handle_network_error(console, error)`

Displays a "Network Error" panel asking the user to check their internet connection.

### `show_error(console, error_key, details=None)`

Looks up `error_key` in the `ERROR_MESSAGES` dictionary and displays the predefined message. Falls back to a generic error if the key is not found.

### `success_message(console, title, message)`

Displays a green-bordered panel for successful operations. Used as a counterpart to error panels after completing actions like adding a wallet or saving settings.

### `format_suggestion(text)`

Returns `text` wrapped in Rich dim markup for inline display: `[dim]Tip: {text}[/dim]`.

## Predefined Error Messages

The `ERROR_MESSAGES` dictionary provides reusable error definitions keyed by scenario name:

| Key | Title | Suggestion |
|---|---|---|
| `no_markets_found` | No Markets Found | Try broader search terms |
| `no_whales_found` | No Whale Activity | Extend time period or lower threshold |
| `no_arbitrage` | No Arbitrage Opportunities | Lower minimum spread or check back later |
| `no_predictions` | No Predictions Available | Try different markets with more data |
| `empty_portfolio` | Empty Portfolio | Add wallet addresses |
| `invalid_market_id` | Invalid Market ID | Market IDs are hex strings starting with `0x` |
| `invalid_wallet` | Invalid Wallet Address | Ethereum addresses are 42 chars starting with `0x` |
| `database_error` | Database Error | Delete `~/.polyterm/data.db` and restart |

## Usage Examples

**In a CLI command, catch and display API errors:**

```python
from polyterm.utils.errors import handle_api_error

try:
    markets = api.get_markets()
except Exception as e:
    handle_api_error(console, e, context="fetching markets")
    return
```

**Show a predefined error when no results are found:**

```python
from polyterm.utils.errors import show_error

if not results:
    show_error(console, "no_arbitrage")
    return
```

**Raise and catch a typed exception:**

```python
from polyterm.utils.errors import ValidationError, display_error

try:
    if not address.startswith("0x") or len(address) != 42:
        raise ValidationError(
            "Invalid wallet address format.",
            suggestion="Ethereum addresses are 42 characters starting with '0x'.",
        )
except ValidationError as e:
    display_error(console, "Validation Error", e.message, e.suggestion)
```

**Display a success confirmation:**

```python
from polyterm.utils.errors import success_message

success_message(console, "Wallet Added", "Successfully tracking 0xabc...123")
```

## Related Features

- **API clients** (`api/gamma.py`, `api/clob.py`, `api/data_api.py`) -- raise exceptions that flow through `handle_api_error()`.
- **Config module** (`utils/config.py`) -- raises `ValueError` on validation failures, caught and displayed via `handle_config_error()`.
- **TUI screens** -- wrap command execution in try/except blocks using these display functions.
- **Tips system** (`utils/tips.py`) -- `format_suggestion()` uses the same dim-text pattern as tips for visual consistency.

Source: `polyterm/utils/errors.py`
