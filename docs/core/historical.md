# Historical

> Historical data API for trade retrieval, OHLCV candle generation, and ML/backtesting exports.

## Overview

The historical module provides a comprehensive API for accessing and processing historical market data. It retrieves trades and market snapshots from the local SQLite database, generates OHLCV (Open-High-Low-Close-Volume) candlestick data at configurable intervals, calculates market statistics (volatility, returns, price ranges), and exports data in CSV and JSON formats suitable for machine learning training and backtesting workflows.

## Key Classes and Functions

### `OHLCV`

Dataclass representing a single candlestick.

```python
@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    trade_count: int = 0
```

Has a `.to_dict()` method for JSON serialization.

### `HistoricalData`

Dataclass that bundles all historical data for a market.

```python
@dataclass
class HistoricalData:
    market_id: str
    market_title: str
    start_time: datetime
    end_time: datetime
    trades: List[Trade] = field(default_factory=list)
    snapshots: List[MarketSnapshot] = field(default_factory=list)
    ohlcv: List[OHLCV] = field(default_factory=list)
```

Has a `.to_dict()` method that serializes all nested data.

### `HistoricalDataAPI`

Main class for historical data operations.

#### Constructor

```python
HistoricalDataAPI(
    database: Database,
    gamma_client: Optional[GammaClient] = None,
    clob_client: Optional[CLOBClient] = None,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_trades` | `(market_id=None, wallet_address=None, start_time=None, end_time=None, min_notional=0, limit=10000) -> List[Trade]` | Retrieve historical trades with multiple filters |
| `get_snapshots` | `(market_id: str, start_time=None, end_time=None, limit=10000) -> List[MarketSnapshot]` | Get historical market snapshots |
| `generate_ohlcv` | `(market_id: str, interval='1h', start_time=None, end_time=None) -> List[OHLCV]` | Generate OHLCV candles from trade data |
| `get_historical_data` | `(market_id: str, start_time=None, end_time=None, include_trades=True, include_snapshots=True, include_ohlcv=True, ohlcv_interval='1h') -> HistoricalData` | Get comprehensive historical data bundle |
| `export_csv` | `(data: HistoricalData, output_path: str, data_type='ohlcv') -> str` | Export data to CSV file |
| `export_json` | `(data: HistoricalData, output_path: str) -> str` | Export complete data to JSON file |
| `get_statistics` | `(market_id: str, start_time=None, end_time=None) -> Dict[str, Any]` | Calculate comprehensive market statistics |

#### Private Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_parse_interval` | `(interval: str) -> int` | Parse interval string to seconds |
| `_floor_timestamp` | `(ts: datetime, interval_seconds: int) -> datetime` | Floor timestamp to interval boundary |
| `_create_candle` | `(timestamp: datetime, trades: List[Trade]) -> OHLCV` | Create OHLCV candle from grouped trades |
| `_calculate_volatility` | `(returns: List[float]) -> float` | Standard deviation of returns |

## Scoring / Algorithms

### OHLCV Candle Generation

1. Trades fetched from database for the specified market and time range
2. Each trade's timestamp is floored to the interval boundary (e.g., `1h` floors to the hour)
3. Trades within the same interval are grouped
4. For each group:
   - `open` = first trade price
   - `high` = max trade price
   - `low` = min trade price
   - `close` = last trade price
   - `volume` = sum of all trade notional values
   - `trade_count` = number of trades

### Supported Intervals

| Interval | String | Seconds |
|----------|--------|---------|
| 1 minute | `"1m"` | 60 |
| 5 minutes | `"5m"` | 300 |
| 15 minutes | `"15m"` | 900 |
| 1 hour | `"1h"` | 3600 |
| 4 hours | `"4h"` | 14400 |
| 1 day | `"1d"` | 86400 |

### Market Statistics

The `get_statistics` method calculates:

- **Trade count**: Total number of trades
- **Total volume**: Sum of all trade notional values
- **Average trade size**: `total_volume / trade_count`
- **Price metrics**: first, last, high, low, average, absolute change, percentage change
- **Returns**: Per-trade percentage returns `(price[i] - price[i-1]) / price[i-1]`
- **Volatility**: Standard deviation of returns `sqrt(sum((r - mean)^2) / n)`
- **Max/Min returns**: Extreme single-trade return values

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| Default lookback | `30` days | When no `start_time` specified |
| `limit` | `10000` | Maximum records per query |
| `ohlcv_interval` | `"1h"` | Default candle interval |
| `min_notional` | `0` | Minimum trade size filter |

## Data Sources

- **Database** (`db/database.py`):
  - `get_trades_by_market(market_id, limit)` -- trades filtered by market
  - `get_trades_by_wallet(wallet_address, limit)` -- trades filtered by wallet
  - `get_recent_trades(hours, limit)` -- recent trades across all markets
  - `get_market_history(market_id, hours, limit)` -- market snapshots
- **Gamma API** (`api/gamma.py`): Market title lookup (optional)
- **CLOB API** (`api/clob.py`): Not directly used but available for future integration

## Output Format

### `get_statistics` returns

```python
{
    "market_id": "abc123",
    "start_time": "2026-03-01T00:00:00",
    "end_time": "2026-04-03T00:00:00",
    "trade_count": 1500,
    "total_volume": 250000.0,
    "avg_trade_size": 166.67,
    "price": {
        "first": 0.45,
        "last": 0.62,
        "high": 0.75,
        "low": 0.38,
        "avg": 0.55,
        "change": 0.17,
        "change_pct": 37.78,
    },
    "returns": {
        "avg": 0.0012,
        "volatility": 0.035,
        "max": 0.15,
        "min": -0.12,
    },
}
```

### CSV Export Formats

#### OHLCV (`data_type='ohlcv'`)

```
timestamp,open,high,low,close,volume,trade_count
2026-04-01T00:00:00,0.45,0.48,0.44,0.47,15000,25
```

#### Trades (`data_type='trades'`)

```
timestamp,market_id,wallet,side,price,size,notional
2026-04-01T12:00:00,abc123,0xabc...,buy,0.45,100,45.0
```

#### Snapshots (`data_type='snapshots'`)

```
timestamp,probability,volume_24h,liquidity,spread
2026-04-01T12:00:00,0.62,50000,25000,0.02
```

### JSON Export

Full `HistoricalData.to_dict()` output with all trades, snapshots, and OHLCV candles.

## External Dependencies

- `csv` (standard library)
- `json` (standard library)
- `pathlib.Path` (standard library)
- `polyterm.db.database.Database`
- `polyterm.db.models.Trade`, `polyterm.db.models.MarketSnapshot`
- `polyterm.api.gamma.GammaClient` (optional)
- `polyterm.api.clob.CLOBClient` (optional)

## Related

- CLI commands: `polyterm chart` (uses historical data for price charts), `polyterm stats` (market statistics), `polyterm export` (data export)
- TUI screens: `7/e` (export), `ch` (chart), `st` (stats)
- Other modules: `core/charts.py` (renders historical data as ASCII charts), `core/correlation.py` (uses price snapshots for correlation calculation), `core/predictions.py` (uses historical trends for prediction signals)
