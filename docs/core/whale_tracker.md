# Whale Tracker

> Whale activity monitoring and insider trading pattern detection.

## Overview

The whale tracker module provides real-time monitoring of large trades and wallet profiling via CLOB WebSocket, with automatic REST polling fallback. It maintains wallet profiles in the database, classifies traders as whales or smart money, and fires callbacks for significant events. The companion `InsiderDetector` class analyzes wallets for potential insider trading patterns using a multi-factor scoring system.

## Key Classes and Functions

### `WhaleTracker`

Monitors markets for whale and smart money activity via WebSocket with REST fallback.

#### Constructor

```python
WhaleTracker(
    database: Database,
    clob_client: CLOBClient,
    min_whale_trade: float = 10000,
    min_smart_money_win_rate: float = 0.70,
    min_smart_money_trades: int = 10,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `process_trade` | `async (trade_data: Dict[str, Any]) -> Optional[Trade]` | Process a trade from WebSocket/REST, update wallet, check for whale/smart money |
| `start_monitoring` | `async (market_slugs: List[str], poll_interval: float = 5.0) -> None` | Start WebSocket monitoring with REST fallback |
| `stop_monitoring` | `() -> None` | Stop all monitoring (WebSocket and REST) |
| `add_whale_callback` | `(callback: Callable[[Trade, Wallet], None]) -> None` | Register callback for whale trade events |
| `add_smart_money_callback` | `(callback: Callable[[Trade, Wallet], None]) -> None` | Register callback for smart money trade events |
| `get_whale_leaderboard` | `(limit: int = 20) -> List[Wallet]` | Get top whale wallets by volume |
| `get_smart_money_leaderboard` | `(limit: int = 20) -> List[Wallet]` | Get top smart money wallets by win rate |
| `get_recent_whale_trades` | `(hours: int = 24) -> List[Trade]` | Get recent large trades |
| `get_wallet_profile` | `(address: str) -> Optional[Dict[str, Any]]` | Get comprehensive wallet profile |
| `track_wallet` | `(address: str, tag: str = 'tracked') -> None` | Add wallet to tracked list |
| `untrack_wallet` | `(address: str, tag: str = 'tracked') -> None` | Remove wallet from tracked list |
| `get_tracked_wallets` | `() -> List[Wallet]` | Get all manually tracked wallets |

### `InsiderDetector`

Detects potential insider trading patterns in wallet behavior.

#### Constructor

```python
InsiderDetector(database: Database)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `calculate_insider_score` | `(wallet: Wallet) -> int` | Calculate insider risk score (0-100) |
| `analyze_wallet` | `(wallet: Wallet) -> Dict[str, Any]` | Comprehensive insider analysis |
| `get_suspicious_wallets` | `(min_score: int = 70) -> List[Dict[str, Any]]` | Get wallets above suspicious threshold |
| `flag_wallet_as_suspicious` | `(address: str) -> None` | Flag wallet and create alert |
| `check_trade_for_insider_signals` | `(trade: Trade, wallet: Wallet) -> Optional[Alert]` | Check a single trade for insider signals |

## Scoring / Algorithms

### Whale Classification

A trade is classified as a whale trade when `notional >= min_whale_trade` (default $10,000).

A wallet is auto-tagged as `'whale'` when `total_volume >= $100,000`.

### Smart Money Classification

A wallet is considered smart money when:
- Win rate >= 70% (`min_smart_money_win_rate`)
- Total trades >= 10 (`min_smart_money_trades`)

Determined via `wallet.is_smart_money()` method on the Wallet model.

### Whale Alert Severity

Severity is calculated as: `min(100, int(trade.notional / 1000))`

A $100,000 trade produces severity 100 (maximum).

### Insider Detection Scoring (0-100)

Four factors, each contributing 0-25 points:

#### Factor 1: Wallet Age (0-25 points)

| Age | Points |
|-----|--------|
| < 1 day | 25 |
| < 7 days | 20 |
| < 30 days | 10 |
| < 90 days | 5 |
| >= 90 days | 0 |

#### Factor 2: Position Size (0-25 points)

| Avg Position Size | Points |
|-------------------|--------|
| > $50,000 | 25 |
| > $25,000 | 20 |
| > $10,000 | 15 |
| > $5,000 | 10 |
| <= $5,000 | 0 |

#### Factor 3: Win Rate Anomaly (0-25 points)

Requires at least 5 trades to evaluate:

| Win Rate | Points |
|----------|--------|
| > 95% | 25 |
| > 85% | 20 |
| > 75% | 10 |
| <= 75% | 0 |

#### Factor 4: Trading Pattern (0-15 points)

| Condition | Points |
|-----------|--------|
| < 10 trades AND > $50,000 total volume | 15 |
| Otherwise | 0 |

### Insider Risk Levels

| Level | Score Range |
|-------|-------------|
| High | 70-100 |
| Medium | 40-69 |
| Low | 0-39 |

### Per-Trade Insider Signals

`check_trade_for_insider_signals()` checks three conditions:

| Signal | Condition | Severity |
|--------|-----------|----------|
| Fresh wallet with large bet | Wallet < 3 days old AND trade >= $10,000 | +30 |
| First trade unusually large | First ever trade AND notional >= $25,000 | +25 |
| High win rate wallet | Win rate > 90% AND >= 5 trades | +20 |

### WebSocket to REST Fallback

The monitoring system uses a two-tier approach:

1. **Primary**: CLOB WebSocket via `clob.subscribe_to_trades()` and `clob.listen_for_trades()`
2. **Fallback**: REST polling via `_run_rest_polling()` when WebSocket permanently fails

REST polling:
- Polls `clob.get_recent_trades()` every `poll_interval` seconds (default 5.0)
- Deduplicates trades using `seen_tx_hashes` set (max 5,000 entries, cleared when exceeded)
- Processes trades through the same `process_trade()` pipeline as WebSocket

### Wallet Profile Updates

On each processed trade, the wallet profile is updated:
- `total_trades` incremented
- `total_volume` accumulated
- `avg_position_size` recalculated
- `largest_trade` updated if exceeded
- `favorite_markets` maintained (last 10)
- Auto-tagged as `'whale'` at $100k total volume

## Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| `min_whale_trade` | $10,000 | Minimum notional for whale classification |
| `min_smart_money_win_rate` | 0.70 | Minimum win rate for smart money |
| `min_smart_money_trades` | 10 | Minimum trades for smart money |
| `max_recent_trades` | 1,000 | In-memory recent trade cache size |
| REST `poll_interval` | 5.0 seconds | REST fallback polling interval |
| REST `MAX_SEEN` | 5,000 | Deduplication set max size |
| Auto-whale threshold | $100,000 | Total volume for auto-whale tagging |

## Data Sources

- **CLOB WebSocket** (`api/clob.py`): Real-time trade data with `maker_address`/`taker_address`
- **CLOB REST API** (`api/clob.py`): Fallback trade polling via `get_recent_trades()`
- **SQLite Database** (`db/database.py`): Wallet profiles, trade history, alerts, smart money wallets
- **Wallet model** (`db/models.py`): `Wallet`, `Trade`, `Alert` dataclasses

## Output Format

### `InsiderDetector.analyze_wallet()` returns:

```python
{
    'address': str,
    'risk_score': int,         # 0-100
    'risk_level': 'high' | 'medium' | 'low',
    'risk_factors': [str],     # List of identified risk factors
    'wallet_age_days': int,
    'total_trades': int,
    'total_volume': float,
    'win_rate': float,
    'avg_position_size': float,
}
```

### Whale/Smart Money Alerts

Stored via `db.insert_alert()` with types:
- `'whale'` -- large trade detected
- `'smart_money'` -- high win-rate wallet traded
- `'insider_suspect'` -- wallet flagged as suspicious
- `'insider_signal'` -- trade exhibits insider patterns

## External Dependencies

- `polyterm.db.database.Database`
- `polyterm.db.models` (`Wallet`, `Trade`, `Alert`)
- `polyterm.api.clob.CLOBClient`
- `polyterm.utils.json_output.safe_float`
- `asyncio` (async monitoring and callbacks)

## Related

- CLI command: `polyterm whales --hours 24`
- TUI screens: `3/w` (whales), `15/follow` (copy trading)
- Interacts with: `predictions.py` (whale and smart money signals), `cluster_detector.py` (wallet cluster analysis), `notifications.py` (alert delivery)
