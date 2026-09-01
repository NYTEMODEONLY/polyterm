# DataAPIClient

> Data API client for Polymarket wallet positions, activity, and trade history.

## Overview

The `DataAPIClient` class provides access to the Polymarket Data API at `data-api.polymarket.com`. It retrieves wallet positions, trading activity, trade history, and profit/loss summaries for any wallet address. Those surfaces are **lagged**. They are not the live CLOB fill tape. Aggregated payloads (`get_wallet_profile`, `get_profit_summary`) are labeled `source=data_api` with `lag=true` / `lagged=true`. CLI/TUI/JSON that prints this data must keep that label. Do not invent a lag duration.

This client replaces the deprecated Subgraph for wallet data and uses the same retry pattern as `CLOBClient` for resilience against rate limits and server errors.

## Key Classes and Functions

### `DataAPIClient`

Client for Polymarket Data API providing wallet-level data.

#### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` or `None` | `"https://data-api.polymarket.com"` | Base URL for the Data API |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `__init__` | `(base_url=None)` | Initialize client with optional custom base URL |
| `get_positions` | `(address, limit=100, offset=0, sort_by="CURRENT", size_threshold=None)` | Get wallet positions. Optional `sizeThreshold` (cashflow mark uses `0`). |
| `get_activity` | `(address, limit=100, offset=0, activity_type=None, sort_direction=None)` | Get wallet activity feed. Optional `type` and `sortDirection`. Cashflow P&L uses `sortDirection=ASC`. |
| `get_trades` | `(address, limit=100, market=None)` | Get wallet trades, optionally filtered by market |
| `get_profit_summary` | `(address)` | Aggregate P&L summary across all positions |
| `get_leaderboard` | `(period="7d", limit=50, sort_by="profit")` | Public `/v1/leaderboard`. `profit`/`volume`/`active` map to PNL/VOL. `winrate` is not mapped to PNL. |
| `close` | `()` | Close the HTTP session |

## API Endpoints Used

All endpoints are on `https://data-api.polymarket.com`:

| Endpoint | Method | Parameters | Description |
|----------|--------|------------|-------------|
| `/positions` | GET | `user`, `limit`, `offset`, `sortBy` | Wallet positions. Current sort keys include `CURRENT` and `CASHPNL` |
| `/activity` | GET | `user`, `limit`, `offset` | Wallet activity feed |
| `/trades` | GET | `user`, `limit`, `market` (optional) | Wallet trade history |
| `/v1/leaderboard` | GET | `timePeriod`, `orderBy`, `limit` | Public trader rankings (`DAY`/`WEEK`/`MONTH`/`ALL`, `PNL`/`VOL`) |

## Configuration

- **Base URL**: `https://data-api.polymarket.com` (configurable via constructor)
- **Default timeout**: 15 seconds per request
- **Default retries**: 3 attempts per request
- No API key required

## Rate Limiting / Error Handling

The `_request` method follows the same retry pattern as `CLOBClient`:

| Condition | Behavior |
|-----------|----------|
| HTTP 429 (rate limited) | Wait `min(2^attempt * 2, 30)` seconds; respects `Retry-After` header (capped at 60s) |
| HTTP 5xx (server error) | Wait `2^attempt` seconds, retry up to `retries - 1` times |
| Timeout | Wait `2^attempt` seconds, retry; raise on final attempt |
| Connection error | Wait `2^attempt` seconds, retry; raise on final attempt |
| All retries exhausted | Raises `Exception` with URL |

## Data Flow

1. **Positions**: `get_positions(address)` -> GET `/positions?user={address}&sortBy=CURRENT` -> returns list of position dicts with fields like `pnl`, `initialValue`, `currentValue`.
2. **Activity**: `get_activity(address)` -> GET `/activity?user={address}` -> returns list of activity items.
3. **Trades**: `get_trades(address, market=...)` -> GET `/trades?user={address}` -> returns list of trade dicts; optionally filtered by `market` parameter.
4. **Profit summary**: `get_profit_summary(address)` -> fetches up to 500 positions sorted by `CASHPNL` -> aggregates `total_pnl`, `total_invested`, `position_count` across all positions. Silently skips positions with unparseable numeric values. This is **not** honest wallet P&L: `/positions.cashPnl` drops redeemed winners. Use `polyterm mywallet --pnl` / `core/pnl_cashflow.py` (activity cashflow + open-size mark) instead.

## External Dependencies

- `requests` -- HTTP client for REST calls

## Related

- **Core modules**: `core/analytics.py` (imports `DataAPIClient` for wallet analytics)
- **Package exports**: Exported via `polyterm.api.__init__` as part of `__all__`
- **Replaces**: `SubgraphClient` (deprecated) for wallet position and trade data
- **Lag labels**: [data_api_lag](data_api_lag.md) (`source=data_api`, `lag=true`, `lagged=true`)
- **CLI commands**: `portfolio` (positions), `wallets --analyze --refresh` (wallet profile), `whales --wallets` (lagged prints via `PrintScanner`), `mywallet --pnl` (activity-cashflow P&L; not `get_profit_summary`)

## June 2026 Wallet Intelligence Methods

The Data API client includes additional read-only helpers for agent and wallet-intelligence workflows:

```python
client.get_holders(market="0x...", limit=100)
client.get_value("0xabc...")
client.get_market_positions("0x...")
client.get_leaderboard(period="7d", limit=50, sort_by="profit")
client.get_closed_positions("0xabc...", limit=50)
client.get_wallet_profile("0xabc...")
```

These methods use the public Data API base URL, `https://data-api.polymarket.com`. Leaderboard calls use the current documented `/v1/leaderboard` endpoint with `timePeriod`, `orderBy`, `limit`, and pagination parameters. The helper maps PolyTerm's `24h`, `7d`, `30d`, and `all` periods to Polymarket's `DAY`, `WEEK`, `MONTH`, and `ALL` values, and maps `profit`/`volume`/`active` to `PNL`/`VOL`. It does not map `winrate` to `PNL`; the CLI refuses `--type winrate` on the Data API source.

The exact holder and ranking surfaces have changed more often than `/positions`, `/closed-positions`, and `/trades`, so callers should handle empty responses or request errors gracefully.

Wallet profile aggregation combines public positions, trades, and value data when available. It does not authenticate, place trades, or access private wallet data.

Identifier requirements:

- Wallet calls use wallet or proxy wallet addresses.
- Market-position and holder calls use public market or token identifiers accepted by the current Data API endpoint.
- CLOB token IDs are not interchangeable with Gamma market IDs unless the endpoint explicitly asks for a token.
- Recent-trader agent tooling computes win rate from closed positions and labels that provenance in `quality_flags`.
