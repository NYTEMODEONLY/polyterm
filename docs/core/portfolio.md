# Portfolio Tracking and Management

> Tracks wallet positions from local trade history, calculates P&L, and provides risk analysis with concentration metrics.

## Overview

The portfolio module rebuilds portfolio state from trade history stored in the local SQLite database, since the previously used Subgraph API is deprecated. It calculates open positions with unrealized P&L, computes realized P&L from closed trades, and performs risk analysis using the Herfindahl-Hirschman Index (HHI) for portfolio concentration. Current market prices are fetched from the Gamma API with a 60-second cache. An optional Polygon RPC client enables on-chain balance verification.

## Key Classes and Functions

### `Position`

Dataclass representing a single open position in a market.

| Field | Type | Description |
|-------|------|-------------|
| `market_id` | `str` | Market identifier |
| `market_title` | `str` | Human-readable market question |
| `outcome` | `str` | `"YES"` or `"NO"` |
| `shares` | `float` | Number of shares held |
| `avg_price` | `float` | Average cost per share |
| `current_price` | `float` | Current market price |
| `cost_basis` | `float` | Total cost of position |
| `current_value` | `float` | Current value (`shares * current_price`) |
| `unrealized_pnl` | `float` | Unrealized profit/loss in dollars |
| `unrealized_pnl_pct` | `float` | Unrealized P&L as percentage of cost basis |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `to_dict` | `() -> Dict[str, Any]` | Serializes position to dict |

### `PortfolioSummary`

Dataclass containing aggregate portfolio statistics and position list.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `wallet_address` | `str` | required | Wallet address |
| `total_positions` | `int` | required | Number of open positions |
| `total_cost_basis` | `float` | required | Sum of all position cost bases |
| `total_current_value` | `float` | required | Sum of all current values |
| `total_unrealized_pnl` | `float` | required | Total unrealized P&L |
| `total_unrealized_pnl_pct` | `float` | required | Total unrealized P&L percentage |
| `realized_pnl` | `float` | required | Realized P&L from closed positions |
| `total_trades` | `int` | required | Total number of trades |
| `win_rate` | `float` | required | Historical win rate |
| `positions` | `List[Position]` | `[]` | List of open positions |
| `updated_at` | `datetime` | `now()` | Timestamp of this summary |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `to_dict` | `() -> Dict[str, Any]` | Serializes summary and all positions to dict |

### `PolygonRPCClient`

Client for reading on-chain data via Polygon JSON-RPC.

**Constructor**: `__init__(self, rpc_url: Optional[str] = None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `rpc_url` | `str` | `"https://polygon-rpc.com"` | Polygon RPC endpoint |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_balance` | `(address: str, token_address: str) -> int` | Gets ERC20 token balance via `balanceOf` call |
| `get_conditional_token_balance` | `(address: str, condition_id: str, outcome_index: int) -> int` | Gets ERC1155 conditional token balance (stub -- returns 0, needs position ID calculation) |
| `get_block_number` | `() -> int` | Gets current Polygon block number |

#### Contract Addresses

| Contract | Address |
|----------|---------|
| CTFExchange | `0x4bFb41d5B3570DeFd03C39a9A4D8dE6Bd8fed8e9` |
| ConditionalTokens | `0x4D97DCd97eC945f40cF65F87097ACe5EA0476045` |

### `PortfolioAnalytics`

Main analytics class that builds portfolios from local trade history and provides risk analysis.

**Constructor**: `__init__(self, database: Database, gamma_client: Optional[GammaClient] = None, polygon_rpc_url: Optional[str] = None)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `database` | `Database` | required | Local SQLite database |
| `gamma_client` | `GammaClient` | `None` | Gamma API client for current prices |
| `polygon_rpc_url` | `str` | `None` | Optional Polygon RPC URL for on-chain verification |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_portfolio` | `(wallet_address: str) -> PortfolioSummary` | Builds full portfolio from trade history. Aggregates positions, calculates P&L, fetches current prices. |
| `get_risk_analysis` | `(wallet_address: str) -> Dict[str, Any]` | Analyzes portfolio risk using HHI concentration index, position percentages, and risk factor identification. |
| `get_performance_history` | `(wallet_address: str, days: int = 30) -> List[Dict]` | Placeholder for daily portfolio snapshots (returns empty list). |
| `render_portfolio_ascii` | `(portfolio: PortfolioSummary) -> str` | Renders portfolio as a formatted ASCII table with summary and position details. |

#### Internal Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_get_current_price` | `(market_id: str, outcome: str) -> float` | Fetches current price from Gamma API with 60-second cache. Defaults to 0.5 if unavailable. |
| `_get_market_title` | `(market_id: str) -> str` | Fetches market title from Gamma API. Falls back to truncated market ID. |
| `_calculate_realized_pnl` | `(trades: List[Trade]) -> float` | Calculates realized P&L using average cost method across all closed trades. |
| `_identify_risk_factors` | `(portfolio: PortfolioSummary) -> List[str]` | Generates human-readable risk factor warnings. |

## Scoring / Algorithms

### Position Building

Positions are reconstructed from trade history by processing trades chronologically:
- **BUY**: Adds shares and increases cost basis
- **SELL**: Reduces shares and decreases cost basis
- Positions with `shares <= 0` are treated as closed and excluded from the open positions list

### Realized P&L Calculation

Uses **average cost method**:
1. Group trades by `market_id:outcome`
2. Process chronologically within each group
3. On SELL: `realized_pnl += sell_notional - (avg_cost * shares_sold)`
4. Average cost updated: `avg_cost = cost_basis / shares`

### Risk Analysis: HHI (Herfindahl-Hirschman Index)

```
HHI = sum((position_value / total_value)^2) * 10000
```

- Range: 0 to 10,000
- Higher values indicate greater concentration

### Concentration Risk Levels

| Max Position % | Risk Level |
|---------------|------------|
| > 50% | `high` |
| > 30% | `medium` |
| <= 30% | `low` |

### Diversification Score

```
diversification = max(0, min(100, 100 - (HHI / 100)))
```

- Range: 0 to 100
- Higher values indicate better diversification

### Risk Factors Detected

| Condition | Warning |
|-----------|---------|
| Single position | "Single position - no diversification" |
| Unrealized loss > 20% | "Significant unrealized loss ({pct}%)" |

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| Price cache TTL | `60` seconds | How long cached prices remain valid |
| Default price | `0.5` | Fallback when API is unavailable |
| RPC timeout | `30` seconds | Polygon RPC call timeout |
| Trade fetch limit | `10,000` | Max trades fetched per wallet |
| Market title truncation | `30` characters | Fallback title length |

## Data Sources

- **Local SQLite database** (`~/.polyterm/data.db`): Trade history and wallet data via `Database` class
- **Gamma REST API**: Current market prices and titles via `GammaClient`
- **Polygon RPC** (optional): On-chain balance verification via `https://polygon-rpc.com`

## Output Format

### `get_portfolio()` return (via `to_dict()`)

```python
{
    'wallet_address': str,
    'total_positions': int,
    'total_cost_basis': float,
    'total_current_value': float,
    'total_unrealized_pnl': float,
    'total_unrealized_pnl_pct': float,
    'realized_pnl': float,
    'total_trades': int,
    'win_rate': float,
    'positions': [Position.to_dict(), ...],
    'updated_at': str,  # ISO format
}
```

### `get_risk_analysis()` return

```python
{
    'wallet_address': str,
    'total_value': float,
    'position_count': int,
    'concentration_risk': str,      # 'high', 'medium', or 'low'
    'max_position_pct': float,
    'hhi_index': float,
    'diversification_score': float,  # 0-100
    'top_positions': [              # Up to 5
        {'market': str, 'percentage': float, 'value': float}
    ],
    'risk_factors': [str, ...],
}
```

## External Dependencies

- `polyterm.db.database.Database` -- local SQLite database
- `polyterm.db.models.Trade`, `polyterm.db.models.Wallet` -- data models
- `polyterm.api.gamma.GammaClient` -- market price and title fetching
- `requests` -- HTTP client for Polygon RPC calls

## Related

- CLI command: `polyterm mywallet -i` (wallet positions), `polyterm pnl` (profit/loss)
- TUI screen: shortcut `p` (portfolio), `mw` (my wallet), `pnl` (profit/loss)
- Related modules: `polyterm/api/data_api.py` (real wallet data from Data API), `polyterm/db/database.py` (trade storage)
