# SubgraphClient

> Legacy GraphQL client for The Graph Protocol subgraph (deprecated).

## Overview

The `SubgraphClient` class was the original client for querying on-chain Polymarket data via The Graph Protocol's GraphQL subgraph. The endpoint has been deprecated and removed by The Graph, so this client is kept solely for backward compatibility. It logs a deprecation warning on first instantiation and will fail on all queries against the original endpoint. New code should use `GammaClient` for market data or `DataAPIClient` for wallet data.

## Key Classes and Functions

### `SubgraphClient`

**DEPRECATED.** Client for the PolyMarket Subgraph via The Graph Protocol.

#### Constructor

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `endpoint` | `str` | `"https://api.thegraph.com/subgraphs/name/polymarket/matic-markets"` | GraphQL endpoint (no longer functional) |

A deprecation warning is logged once (module-level `_DEPRECATION_WARNED` flag) on first instantiation.

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `query` | `(query_string: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]` | Execute a raw GraphQL query |
| `get_market_trades` | `(market_id: str, first: int = 100, skip: int = 0, order_by: str = "timestamp", order_direction: str = "desc") -> List[Dict[str, Any]]` | Get trades for a market |
| `get_market_volume` | `(market_id: str, start_time: Optional[int] = None, end_time: Optional[int] = None) -> Dict[str, Any]` | Get aggregated volume for a market |
| `get_whale_trades` | `(min_notional: float = 10000, first: int = 100, skip: int = 0) -> List[Dict[str, Any]]` | Get large trades filtered by notional value |
| `get_user_positions` | `(wallet_address: str) -> List[Dict[str, Any]]` | Get positions for a wallet address |
| `get_market_liquidity_changes` | `(market_id: str, first: int = 100) -> List[Dict[str, Any]]` | Get liquidity change events |
| `get_market_statistics` | `(market_id: str) -> Dict[str, Any]` | Get comprehensive market statistics |
| `get_trending_markets_by_volume` | `(time_window: int = 86400, first: int = 10) -> List[Dict[str, Any]]` | Get trending markets by recent volume |

## API Endpoints Used

| Endpoint | Method | Description |
|----------|--------|-------------|
| `https://api.thegraph.com/subgraphs/name/polymarket/matic-markets` | POST (GraphQL) | **DEPRECATED** -- The Graph has removed this subgraph |

### GraphQL Queries

| Query | Variables | Description |
|-------|-----------|-------------|
| `GetMarketTrades` | `marketId`, `first`, `skip`, `orderBy`, `orderDirection` | Fetch trades with pagination and ordering |
| `GetMarketVolume` | `marketId`, `startTime`, `endTime` | Aggregate volume with optional time range filter |
| `GetWhaleTrades` | `first`, `skip` | Fetch all trades, then client-side filter by `notional >= min_notional` |
| `GetUserPositions` | `walletAddress` | Fetch positions for a wallet (address lowercased) |
| `GetLiquidityChanges` | `marketId`, `first` | Fetch liquidity add/remove events |
| `GetMarketStats` | `marketId` | Fetch comprehensive market metadata |
| `GetTrendingMarkets` | `startTime`, `first` | Fetch markets ordered by total volume |

## Configuration

No configuration options. The endpoint URL is hardcoded and no longer functional.

## Rate Limiting / Error Handling

- No rate limiting is implemented (The Graph handled rate limits server-side).
- All query failures raise `Exception` with the message `"GraphQL query failed: {error}"`.
- If the `gql` library is not installed, `query` raises `Exception` with install instructions.
- The `_deprecated` attribute is set to `True` on initialization.

## Data Flow

1. Caller invokes a query method (e.g., `get_market_trades`).
2. Method constructs a GraphQL query string and variables dict.
3. `query` method executes via `gql.Client.execute()`.
4. Results are extracted from the response by expected key (e.g., `"trades"`, `"market"`).
5. Some methods apply client-side filtering (e.g., `get_whale_trades` filters by notional value after fetching).

## External Dependencies

- `gql` with `gql[all]` extras (optional) -- GraphQL client library; guarded by `HAS_GQL` flag
- `gql.transport.requests.RequestsHTTPTransport` -- HTTP transport for GraphQL queries

## Related

- **Replaced by**: `GammaClient` (market data), `DataAPIClient` (wallet positions and trades), `CLOBClient` (order book and trade data)
- **Current usage**: None -- `SubgraphClient` is not imported by any other module in the codebase. It is retained for backward compatibility only.
- **Not exported**: Not included in `polyterm.api.__init__.__all__`
