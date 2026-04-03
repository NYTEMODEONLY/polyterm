# Order Book Analysis

> Real-time and REST-based order book analysis with ASCII depth charts, iceberg detection, slippage calculation, and live WebSocket state management.

## Overview

The orderbook module provides three layers of functionality: a `LiveOrderBook` class that maintains thread-safe in-memory order book state from CLOB WebSocket updates, an `OrderBookAnalyzer` that performs comprehensive analysis (support/resistance, large orders, imbalance, slippage), and ASCII visualization of bid/ask depth. It supports both REST-fetched snapshots and real-time WebSocket feeds with market resolution detection.

## Key Classes and Functions

### `OrderBookLevel`

Dataclass representing a single price level.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `price` | `float` | required | Price at this level |
| `size` | `float` | required | Order size in shares |
| `cumulative_size` | `float` | `0.0` | Running total of size from top of book |
| `order_count` | `int` | `0` | Number of orders at this level |

### `OrderBookAnalysis`

Dataclass containing full analysis results.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market or token identifier |
| `timestamp` | `datetime` | Analysis timestamp |
| `best_bid` | `float` | Highest bid price |
| `best_ask` | `float` | Lowest ask price |
| `spread` | `float` | Absolute spread (ask - bid) |
| `spread_pct` | `float` | Spread as percentage of mid price |
| `mid_price` | `float` | Midpoint of best bid and ask |
| `bid_depth` | `float` | Total bid volume (shares) |
| `ask_depth` | `float` | Total ask volume (shares) |
| `imbalance` | `float` | -1 to 1; positive = more bid volume |
| `support_levels` | `List[float]` | Detected support prices (up to 5) |
| `resistance_levels` | `List[float]` | Detected resistance prices (up to 5) |
| `large_bids` | `List[OrderBookLevel]` | Bids with notional >= threshold |
| `large_asks` | `List[OrderBookLevel]` | Asks with notional >= threshold |
| `warnings` | `List[str]` | Generated warning messages |

### `LiveOrderBook`

Thread-safe in-memory order book maintained by CLOB WebSocket updates. Uses a `threading.Lock` so the sync CLI refresh loop can safely read while the async WS listener writes.

**Constructor**: `__init__(self, token_id: str)`

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `handle_message` | `(data: Dict[str, Any]) -> None` | Processes a CLOB WS message. Dispatches by type: `book`, `last_trade_price`, `price_change`, `market_resolved`. Fires optional `on_update` callback after each update. |
| `get_snapshot` | `() -> Dict[str, Any]` | Returns a REST-compatible snapshot with sorted bids (descending) and asks (ascending), plus last trade price and message count. |
| `get_top_of_book` | `() -> Dict[str, Optional[float]]` | Returns best bid, best ask, spread, mid price, and last trade price. |
| `get_depth` | `(levels: int = 10) -> Dict[str, Any]` | Returns top N bid/ask levels with cumulative sizes and total depth. |
| `set_on_update` | `(callback: Optional[Callable]) -> None` | Registers a callback fired after each WS update. |

#### Properties

| Property | Type | Description |
|----------|------|-------------|
| `is_ready` | `bool` | True once at least one book message has been received |
| `message_count` | `int` | Total WS messages processed |
| `last_update` | `Optional[datetime]` | Timestamp of most recent update |
| `resolved` | `bool` | Whether market has been resolved |
| `resolution_data` | `Optional[Dict]` | Resolution details if resolved; contains `token_id`, `outcome`, `winning_price`, `resolved_at` |

#### Internal Methods

| Method | Description |
|--------|-------------|
| `_apply_book` | Applies full or incremental book snapshot. Size of `"0"` removes a level. |
| `_apply_last_trade_price` | Updates last trade price from WS message. |
| `_apply_price_change` | Updates last price change from WS message. |
| `_apply_resolution` | Captures market resolution outcome, price, and timestamp. |

### `OrderBookAnalyzer`

Main analysis class combining REST and live WebSocket order book analysis.

**Constructor**: `__init__(self, clob_client: CLOBClient, large_order_threshold: float = 10000)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `clob_client` | `CLOBClient` | required | CLOB REST/WS client |
| `large_order_threshold` | `float` | `10000` | Notional value threshold ($) for flagging large orders |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `analyze` | `(market_id: str, depth: int = 50) -> Optional[OrderBookAnalysis]` | Fetches order book via REST and performs full analysis. |
| `analyze_live` | `(token_id: str) -> Optional[OrderBookAnalysis]` | Same analysis but from live WS state instead of REST. |
| `start_live_feed` | `async (token_ids: List[str], on_update=None, on_resolution=None) -> Dict[str, LiveOrderBook]` | Creates `LiveOrderBook` instances, subscribes via CLOB WS, and returns live books. Caller must also run `clob.listen_orderbook()`. |
| `get_live_prices` | `(token_ids: List[str]) -> Dict[str, Dict[str, Optional[float]]]` | Returns mid prices and spreads for multiple tokens from live feeds. Designed for the arb scanner. |
| `get_live_book` | `(token_id: str) -> Optional[LiveOrderBook]` | Returns the live book for a token, or None if not started. |
| `stop_live_feed` | `() -> None` | Clears live book references. Caller should close WS separately. |
| `calculate_slippage` | `(market_id: str, side: str, size: float) -> Dict[str, Any]` | Simulates filling an order against the book. Returns avg price, slippage, total cost, and levels used. |
| `render_ascii_depth_chart` | `(market_id: str, width: int = 60, height: int = 20, depth: int = 20) -> str` | Renders an ASCII depth chart showing bid/ask cumulative depth as horizontal bar charts. |
| `detect_iceberg_orders` | `(market_id: str, min_replenish_count: int = 3) -> List[Dict]` | Detects potential hidden orders by looking for repeated size patterns (rounded to nearest 100, size >= 1000). |
| `format_analysis` | `(analysis: OrderBookAnalysis) -> str` | Formats an analysis result as a human-readable text block. |
| `get_order_book` | `(market_id: str, depth: int = 50) -> Dict[str, Any]` | Fetches raw order book from CLOB REST API. |

## Scoring / Algorithms

### Liquidity Imbalance

```
imbalance = (bid_depth - ask_depth) / (bid_depth + ask_depth)
```

- Range: -1.0 to +1.0
- Positive: more bid volume (buying pressure)
- Negative: more ask volume (selling pressure)
- Warning triggered when `abs(imbalance) > 0.5`

### Support/Resistance Detection

Levels are identified by finding price levels where order size exceeds `min_size_multiple` (default 3.0x) times the average level size. Up to 5 levels returned per side.

### Large Order Detection

A level is flagged as a "large order" when its notional value (`size * price`) meets or exceeds `large_order_threshold` (default $10,000).

### Iceberg Detection (Simplified)

Scans for repeated order sizes (rounded to nearest 100) that appear at 2+ price levels with size >= 1,000 shares. This is a heuristic approach; true iceberg detection requires monitoring the book over time.

### Slippage Calculation

Walks the order book level by level, filling the requested size at each price until complete. Returns:
- `avg_price`: Volume-weighted average execution price
- `slippage`: `abs(avg_price - best_price)`
- `slippage_pct`: `(slippage / best_price) * 100`

### Warnings Generated

| Condition | Warning |
|-----------|---------|
| `abs(imbalance) > 0.5` | "High liquidity imbalance towards {bids/asks}" |
| `spread_pct > 5` | "Wide spread: {pct}%" |
| Large orders present | "Large orders detected: N bids, N asks" |

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| `large_order_threshold` | `$10,000` | Notional value to flag as large order |
| `min_size_multiple` | `3.0` | Multiplier of avg size for support/resistance detection |
| Default depth | `50` levels | Price levels fetched from REST |
| ASCII chart defaults | `60w x 20h` | Default chart dimensions |

## Data Sources

- **CLOB REST API**: `CLOBClient.get_order_book()` for point-in-time snapshots
- **CLOB WebSocket**: `wss://ws-subscriptions-clob.polymarket.com/ws/market` for real-time updates
  - Message types: `book`, `last_trade_price`, `price_change`, `market_resolved`
  - Subscription includes `custom_feature_enabled: True` for settlement events

## Output Format

### `get_snapshot()` (LiveOrderBook)

```python
{
    "bids": [{"price": "0.55", "size": "1200"}, ...],  # Descending by price
    "asks": [{"price": "0.56", "size": "800"}, ...],   # Ascending by price
    "last_trade_price": float or None,
    "last_price_change": float or None,
    "timestamp": str or None,  # ISO format
    "message_count": int,
}
```

### `calculate_slippage()` return

```python
{
    'side': str,           # 'buy' or 'sell'
    'size': float,         # Requested order size
    'best_price': float,   # Top-of-book price
    'avg_price': float,    # Volume-weighted average fill price
    'slippage': float,     # Absolute price impact
    'slippage_pct': float, # Percentage price impact
    'total_cost': float,   # Total cost of the order
    'levels_used': int,    # Number of price levels consumed
}
```

### `resolution_data` property

```python
{
    "token_id": str,
    "outcome": str,         # "YES" or "NO"
    "winning_price": float,
    "resolved_at": datetime,
}
```

## External Dependencies

- `polyterm.api.clob.CLOBClient` -- CLOB REST and WebSocket client
- `polyterm.utils.json_output.safe_float` -- safe float parsing
- `threading` -- thread safety for live book (stdlib)
- `asyncio` -- async WebSocket feed management (stdlib)

## Related

- CLI command: `polyterm orderbook <token_id> --live --refresh 0.5`
- TUI screen: shortcut `ob` (order book), `dp` (depth chart)
- Related modules: `polyterm/core/arbitrage.py` (uses `get_live_prices()` for WS-fed arb detection), `polyterm/cli/commands/orderbook.py` (`LiveOrderbookDisplay` TUI screen)
