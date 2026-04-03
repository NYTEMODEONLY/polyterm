# JSON Output -- Scriptable JSON interface for all CLI commands

Provides a custom JSON encoder, data formatters, and a context-manager class that together enable every CLI command to support `--format json` output for scripting and automation.

## Overview

All PolyTerm CLI commands accept a `--format json` flag that suppresses Rich terminal output and instead emits structured JSON to stdout. This module contains the serialization infrastructure: a `JSONEncoder` that handles datetime objects, dataclasses, and objects with `to_dict()` or `__dict__` attributes; a collection of `format_*_json()` functions that normalize raw API data into clean, consistent dictionaries; and a `JSONOutput` context manager that accumulates data during command execution and prints it as JSON on exit.

The `safe_float()` helper is used throughout to safely coerce values that may arrive from APIs as strings, `None`, or missing keys.

## Key Classes and Functions

### `JSONEncoder(json.JSONEncoder)`

Custom encoder registered with `json.dumps()`. Handles types that the default encoder cannot serialize:

| Type | Serialization |
|---|---|
| `datetime` | ISO 8601 string via `.isoformat()` |
| Dataclass | Dictionary via `dataclasses.asdict()` |
| Object with `to_dict()` | Result of calling `obj.to_dict()` |
| Object with `__dict__` | The instance's `__dict__` |

Falls through to the default encoder for all other types.

### `safe_float(value, default=0.0)`

Attempts `float(value)`. Returns `default` on `None`, empty string, `ValueError`, or `TypeError`. Used throughout the format functions to handle inconsistent API responses.

```python
safe_float("1.23")     # 1.23
safe_float(None)       # 0.0
safe_float("", 0.5)   # 0.5
safe_float("abc")      # 0.0
```

### `output_json(data, pretty=True)`

Serializes `data` to a JSON string using `JSONEncoder`. When `pretty` is `True` (the default), output is indented with 2 spaces. Returns the string without printing it.

### `print_json(data, pretty=True)`

Calls `output_json()` and prints the result to stdout. This is the most common entry point for simple one-shot JSON output.

### `JSONOutput` (Context Manager)

Accumulates key-value data during command execution and prints it as JSON when the context exits. Intended for commands that build their output incrementally.

```python
with JSONOutput(enabled=is_json_mode) as out:
    out.add("markets", formatted_markets)
    out.add("timestamp", datetime.now())
    out.set_success()
# If enabled, prints JSON on exit. If not enabled, does nothing.
```

**Methods:**

- `add(key, value)` -- Store a key-value pair in the output dictionary.
- `set_error(error)` -- Set `error` message and mark `success` as `False`.
- `set_success()` -- Mark `success` as `True`.

When `enabled` is `False`, no output is produced regardless of what data was added. This lets commands unconditionally use the context manager and only produce JSON when the flag is active.

### Data Formatters

Each formatter normalizes raw API data into a clean dictionary with consistent field names:

**`format_market_json(market)`** -- Extracts and normalizes a single market dictionary. Parses `outcomePrices` (which may be a JSON string or list), computes `yes_price`, `no_price`, and `probability`. Output fields: `id`, `slug`, `title`, `description`, `category`, `yes_price`, `no_price`, `probability`, `volume_24h`, `liquidity`, `end_date`, `active`, `closed`, `resolution`.

**`format_markets_json(markets)`** -- Applies `format_market_json()` to a list of markets.

**`format_trade_json(trade)`** -- Normalizes trade data. Output fields: `market_id`, `market_slug`, `wallet_address`, `side`, `outcome`, `price`, `size`, `notional`, `timestamp`, `tx_hash`. Handles both CLOB-style and Gamma-style field names.

**`format_wallet_json(wallet)`** -- Normalizes wallet data. Accepts objects with `to_dict()` or plain dictionaries. Adds computed fields `is_whale` (volume >= 100,000) and `is_smart_money` (win_rate >= 0.70 and trades >= 10).

**`format_alert_json(alert)`** -- Normalizes alert data. Output fields: `id`, `type`, `market_id`, `wallet_address`, `severity`, `message`, `created_at`, `acknowledged`.

**`format_arbitrage_json(arb)`** -- Normalizes an `ArbitrageResult` object. Includes both raw `spread` and computed `spread_pct` (percentage). Serializes `timestamp` to ISO format.

**`format_orderbook_json(analysis)`** -- Normalizes an `OrderBookAnalysis` object. Converts `large_bids` and `large_asks` from objects to `{price, size}` dictionaries. Includes `support_levels`, `resistance_levels`, and `warnings`.

## Usage Examples

**Simple JSON output in a CLI command:**

```python
import click
from polyterm.utils.json_output import print_json, format_markets_json

@click.command()
@click.option("--format", "output_format", type=click.Choice(["text", "json"]))
def monitor(output_format):
    markets = api.get_markets()
    if output_format == "json":
        print_json({"markets": format_markets_json(markets)})
        return
    # ... Rich table output ...
```

**Using the JSONOutput context manager:**

```python
from polyterm.utils.json_output import JSONOutput

with JSONOutput(enabled=(output_format == "json")) as out:
    try:
        arbs = scanner.find_arbitrage()
        out.add("opportunities", [format_arbitrage_json(a) for a in arbs])
        out.add("count", len(arbs))
        out.set_success()
    except Exception as e:
        out.set_error(str(e))
```

**Piping JSON output in a shell pipeline:**

```bash
polyterm monitor --format json --once | jq '.markets[] | select(.probability > 80)'
polyterm whales --format json --hours 4 | jq '.trades | length'
```

## Related Features

- **All CLI commands** (`cli/commands/`) -- every command checks for `--format json` and uses these utilities.
- **Error module** (`utils/errors.py`) -- when JSON mode is active, commands may use `JSONOutput.set_error()` instead of `display_error()`.
- **Data models** (`db/models.py`) -- model classes implement `to_dict()` which the `JSONEncoder` recognizes.
- **API clients** (`api/`) -- return raw dictionaries that the format functions normalize.

Source: `polyterm/utils/json_output.py`
