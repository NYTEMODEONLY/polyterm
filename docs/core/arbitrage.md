# Arbitrage

> Cross-market arbitrage scanner for intra-market, correlated, and cross-platform opportunities.

## Overview

The arbitrage module scans for price discrepancies that can be exploited for profit. It supports three types of arbitrage: intra-market (YES + NO prices don't sum to $1.00), correlated market (similar events with different prices), and cross-platform (Polymarket vs Kalshi). The scanner integrates with live WebSocket order book data for lower-latency spread detection and stores discovered opportunities in the local SQLite database.

## Key Classes and Functions

### `ArbitrageResult`

Dataclass representing a single arbitrage opportunity.

```python
@dataclass
class ArbitrageResult:
    type: str                    # 'intra_market', 'correlated', 'cross_platform'
    market1_id: str
    market2_id: str
    market1_title: str
    market2_title: str
    market1_yes_price: float
    market1_no_price: float
    market2_yes_price: float     # default 0.0
    market2_no_price: float      # default 0.0
    spread: float                # default 0.0
    expected_profit_pct: float   # default 0.0
    expected_profit_usd: float   # for $100 bet, default 0.0
    fees: float                  # default 0.0
    net_profit: float            # default 0.0
    timestamp: datetime          # auto-set to now
    confidence: str              # 'low', 'medium', 'high'
```

### `ArbitrageScanner`

Main scanner for intra-market and correlated market arbitrage.

#### Constructor

```python
ArbitrageScanner(
    database: Database,
    gamma_client: GammaClient,
    clob_client: CLOBClient,
    min_spread: float = 0.025,           # 2.5% minimum spread
    polymarket_fee: float = 0.02,        # 2% winner fee
    orderbook_analyzer: Optional[OrderBookAnalyzer] = None,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `scan_intra_market_arbitrage` | `(markets: List[Dict]) -> List[ArbitrageResult]` | Find markets where YES + NO < $0.975 |
| `scan_correlated_markets` | `(markets: List[Dict], similarity_threshold: float = 0.8) -> List[ArbitrageResult]` | Find price discrepancies between similar markets |
| `scan_all` | `() -> Dict[str, List[ArbitrageResult]]` | Run all scan types (async) |
| `get_best_opportunities` | `(limit: int = 10) -> List[ArbitrageResult]` | Get top opportunities sorted by net profit |
| `format_opportunity` | `(arb: ArbitrageResult) -> str` | Format opportunity for terminal display |

#### Private Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_get_live_prices_for_market` | `(market: Dict) -> Optional[Dict[str, float]]` | Get YES/NO mid-prices from live WebSocket feeds |
| `_extract_token_ids` | `(market: Dict) -> List[str]` | Extract CLOB token IDs from Gamma market dict |
| `_calculate_title_similarity` | `(title1: str, title2: str) -> float` | Jaccard word-overlap similarity (excluding stop words) |
| `_get_market_prices` | `(event: Dict) -> Optional[Dict[str, float]]` | Extract prices, preferring live WS data over REST |
| `_store_opportunity` | `(result: ArbitrageResult) -> None` | Persist opportunity to database |

### `KalshiArbitrageScanner`

Cross-platform arbitrage scanner comparing Polymarket and Kalshi prices.

#### Constructor

```python
KalshiArbitrageScanner(
    database: Database,
    gamma_client: GammaClient,
    kalshi_api_key: str = "",
    kalshi_base_url: str = "https://trading-api.kalshi.com/trade-api/v2",
    polymarket_fee: float = 0.02,
    kalshi_fee: float = 0.007,
)
```

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `get_kalshi_markets` | `() -> List[Dict]` | Fetch open markets from Kalshi API |
| `match_markets` | `(pm_markets: List[Dict], kalshi_markets: List[Dict]) -> List[Tuple[Dict, Dict, float]]` | Match markets across platforms by title similarity (>= 0.7) |
| `scan_cross_platform_arbitrage` | `(min_spread: float = 0.03) -> List[ArbitrageResult]` | Find cross-platform arbitrage opportunities |

## Scoring / Algorithms

### Intra-Market Arbitrage

```
total = yes_price + no_price
if total < (1.0 - min_spread):   # default: total < 0.975
    spread = 1.0 - total
    gross_profit_pct = (spread / total) * 100
    fee_on_winning = 0.02 * (1.0 - min(yes_price, no_price))
    net_profit = spread - fee_on_winning
```

- Confidence: `"high"` if spread > 5%, otherwise `"medium"`
- Results sorted by `net_profit` descending

### Correlated Market Arbitrage

1. Markets grouped by category (extracted from tags or title keywords: politics, crypto, trump, economics, other)
2. Within each category, all pairs compared via Jaccard word-overlap similarity
3. Pairs with similarity >= `similarity_threshold` (default 0.8) and price difference >= `min_spread` are flagged
4. Fee calculation: `0.02 * (1.0 - buy_price)`
5. Confidence: always `"low"` (correlated arbitrage is inherently riskier)

### Cross-Platform Arbitrage (Kalshi)

1. Title matching score >= 0.7 with key-term boost (+0.2 for matches on: trump, biden, election, bitcoin, fed, rate, president)
2. Combined fees: `pm_fee + kalshi_fee` on winnings
3. Confidence: `"medium"` if similarity > 0.85, otherwise `"low"`
4. Default Kalshi fee: 0.7%

### Live WebSocket Price Priority

When an `OrderBookAnalyzer` is provided, the scanner prefers live mid-prices from WebSocket feeds over REST snapshot prices. If only one side (YES or NO) has live data, the other is derived as `1.0 - known_price`.

## Configuration

| Parameter | Default | Description |
|-----------|---------|-------------|
| `min_spread` | `0.025` (2.5%) | Minimum spread to flag intra-market arbitrage |
| `polymarket_fee` | `0.02` (2%) | Polymarket taker fee on winnings |
| `kalshi_fee` | `0.007` (0.7%) | Kalshi fee rate |
| `similarity_threshold` | `0.8` | Minimum title similarity for correlated arb |
| `cache_ttl` | `30` seconds | Market data cache lifetime |

## Data Sources

- **Gamma API** (`api/gamma.py`): Market listings, outcome prices, tags, categories
- **CLOB API** (`api/clob.py`): Token IDs for live price lookup
- **OrderBookAnalyzer** (`core/orderbook.py`): Live WebSocket mid-prices (optional)
- **Kalshi API**: External REST API (requires API key)
- **Database** (`db/database.py`): Opportunity storage and retrieval

## Output Format

### `scan_all` returns

```python
{
    'intra_market': List[ArbitrageResult],
    'correlated': List[ArbitrageResult],
}
```

### `format_opportunity` example output

```
[Intra-Market Arbitrage]
Market: Will Bitcoin hit $100k by end of 2025?
YES: $0.45 + NO: $0.50 = $0.95
Spread: 5.0%
Expected Profit: $3.10 (on $100 bet)
Confidence: medium
```

## External Dependencies

- `polyterm.db.database.Database`
- `polyterm.db.models.ArbitrageOpportunity`
- `polyterm.api.gamma.GammaClient`
- `polyterm.api.clob.CLOBClient`
- `polyterm.core.orderbook.OrderBookAnalyzer` (optional, for live prices)
- `requests` (for Kalshi API, imported lazily)

## Related

- CLI commands: `polyterm arbitrage --min-spread 0.025`
- TUI screens: `9/arb` (arbitrage scanner)
- Other modules: `core/negrisk.py` (multi-outcome NegRisk arbitrage), `core/orderbook.py` (live order book for price feeds)
