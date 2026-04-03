# Config -- TOML-based configuration management for PolyTerm

The `Config` class provides centralized configuration with sensible defaults, dot-notation access, type-safe validation, and automatic deep merging of user overrides.

## Overview

PolyTerm stores its configuration at `~/.polyterm/config.toml`. On startup, the `Config` class loads this file and deep-merges it with a comprehensive `DEFAULT_CONFIG` dictionary so that every key always has a value. If the file does not exist or cannot be parsed, the defaults are used silently. Configuration changes made via `set()` are held in memory until `save()` writes them back to disk.

The class is used throughout the codebase -- CLI commands, TUI screens, API clients, and core logic all instantiate or receive a `Config` object to read settings.

## Key Classes and Functions

### `Config`

**Constructor**

```python
Config(config_path: Optional[str] = None)
```

When `config_path` is omitted, the default location `~/.polyterm/config.toml` is used. Passing a custom path is useful in tests (see Testing Notes below).

**`get(key, default=None)`** -- Read a value using dot notation. Walks nested dictionaries one segment at a time and returns `default` if any segment is missing.

```python
config.get("alerts.probability_threshold")   # -> 10.0
config.get("api.gamma_api_key")              # -> ""
config.get("nonexistent.key", "fallback")    # -> "fallback"
```

**`set(key, value)`** -- Write a value using dot notation. Creates intermediate dictionaries if needed. If a `VALIDATION_RULES` entry exists for the key, the value is coerced to the expected type and checked against min/max bounds. Raises `ValueError` on failure.

```python
config.set("alerts.probability_threshold", 15.0)  # OK
config.set("alerts.check_interval", 2)             # ValueError: must be between 5 and 3600
```

**`save()`** -- Persist the current in-memory config to `~/.polyterm/config.toml`. Creates the parent directory if it does not exist.

**`_deep_merge(base, update)`** -- Recursively merges `update` into `base`. Nested dictionaries are merged rather than replaced, so a user config that sets only `alerts.probability_threshold` will not overwrite the other `alerts` defaults.

### Convenience Properties

The class exposes frequently accessed values as read-only properties to avoid dot-notation strings scattered through code:

| Property | Config Key | Default |
|---|---|---|
| `gamma_api_key` | `api.gamma_api_key` | `""` |
| `gamma_base_url` | `api.gamma_base_url` | `https://gamma-api.polymarket.com` |
| `gamma_markets_endpoint` | `api.gamma_markets_endpoint` | `/events` |
| `clob_endpoint` | `api.clob_endpoint` | `wss://ws-live-data.polymarket.com` |
| `clob_rest_endpoint` | `api.clob_rest_endpoint` | `https://clob.polymarket.com` |
| `subgraph_endpoint` | `api.subgraph_endpoint` | Thegraph URL |
| `kalshi_api_key` | `api.kalshi_api_key` | `""` |
| `kalshi_base_url` | `api.kalshi_base_url` | Kalshi trading API URL |
| `probability_threshold` | `alerts.probability_threshold` | `10.0` |
| `volume_threshold` | `alerts.volume_threshold` | `50.0` |
| `check_interval` | `alerts.check_interval` | `60` |
| `wallet_address` | `wallet.address` | `""` |
| `notification_config` | `notifications` | Full notifications dict |
| `whale_tracking_config` | `whale_tracking` | Full whale tracking dict |
| `arbitrage_config` | `arbitrage` | Full arbitrage dict |

### Wallet Management

Three helper methods manage the `wallet.tracked_wallets` list:

- **`get_tracked_wallets()`** -- Returns the current list (or `[]`).
- **`add_tracked_wallet(address)`** -- Appends `address` if not already present.
- **`remove_tracked_wallet(address)`** -- Removes `address` if present.

These do not call `save()` automatically; the caller is responsible for persisting changes.

### Validation Rules

`VALIDATION_RULES` is a class-level dictionary mapping dot-notation keys to `(type, min, max)` tuples. When `set()` is called for a key that appears here, the value is coerced to `type` and checked against the bounds.

Validated keys include:

| Key | Type | Min | Max |
|---|---|---|---|
| `alerts.probability_threshold` | float | 0.1 | 100.0 |
| `alerts.volume_threshold` | float | 0.0 | 10000.0 |
| `alerts.check_interval` | int | 5 | 3600 |
| `display.max_markets` | int | 1 | 200 |
| `display.refresh_rate` | int | 1 | 60 |
| `whale_tracking.min_whale_trade` | float | 100 | 10000000 |
| `whale_tracking.min_smart_money_win_rate` | float | 0.0 | 1.0 |
| `whale_tracking.min_smart_money_trades` | int | 1 | 10000 |
| `whale_tracking.insider_alert_threshold` | int | 0 | 100 |
| `arbitrage.min_spread` | float | 0.001 | 1.0 |
| `arbitrage.polymarket_fee` | float | 0.0 | 0.5 |
| `arbitrage.kalshi_fee` | float | 0.0 | 0.5 |
| `data_validation.max_market_age_hours` | int | 1 | 720 |
| `data_validation.min_volume_threshold` | float | 0.0 | 1000000 |

### DEFAULT_CONFIG Sections

The full default configuration tree:

- **alerts** -- `probability_threshold` (10.0), `volume_threshold` (50.0), `check_interval` (60)
- **api** -- Gamma, CLOB, Subgraph, and Kalshi endpoints and keys
- **wallet** -- `address`, `tracked_wallets` list
- **display** -- `use_colors` (True), `max_markets` (20), `refresh_rate` (2)
- **data_validation** -- `max_market_age_hours` (24), `require_volume_data` (True), `min_volume_threshold` (0.01), `reject_closed_markets` (True), `enable_api_fallback` (True)
- **notifications** -- `desktop`, `sound`, `webhook`, `quiet_hours_start/end`, `min_change`, `min_volume`, plus nested sections for `telegram`, `discord`, `system`, `sound_file`, and `email` (with SMTP settings)
- **whale_tracking** -- `min_whale_trade` (10000), `min_smart_money_win_rate` (0.70), `min_smart_money_trades` (10), `insider_alert_threshold` (70)
- **arbitrage** -- `min_spread` (0.025), `include_kalshi` (False), `polymarket_fee` (0.02), `kalshi_fee` (0.007)

## Usage Examples

**Read settings in a CLI command:**

```python
from polyterm.utils.config import Config

config = Config()
threshold = config.probability_threshold          # 10.0
wallets = config.get_tracked_wallets()            # []
arb_config = config.arbitrage_config              # {"min_spread": 0.025, ...}
```

**Modify and persist settings (e.g., from the settings screen):**

```python
config = Config()
config.set("display.max_markets", 50)
config.set("whale_tracking.min_whale_trade", 25000)
config.add_tracked_wallet("0xabc123...")
config.save()
```

**Use a temporary config in tests:**

```python
def test_config(tmp_path):
    config = Config(config_path=str(tmp_path / "config.toml"))
    config.set("alerts.check_interval", 10)
    config.save()
    reloaded = Config(config_path=str(tmp_path / "config.toml"))
    assert reloaded.check_interval == 10
```

## Related Features

- **Settings TUI screen** (`tui/screens/`) -- provides an interactive interface for editing config values.
- **Notification system** (`utils/notifications.py`, `core/notifications.py`) -- reads `notifications.*` config to determine delivery channels.
- **Arbitrage scanner** (`core/arbitrage.py`) -- reads `arbitrage.*` for spread thresholds and fee rates.
- **Whale tracker** (`core/whale_tracker.py`) -- reads `whale_tracking.*` for trade-size and win-rate thresholds.
- **Data validation** -- API clients check `data_validation.*` to filter stale or closed markets.

Source: `polyterm/utils/config.py`
