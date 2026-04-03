# Data Models (`polyterm/db/models.py`)

Dataclass models for serializing and deserializing PolyTerm database records.

## Overview

The models module defines six `@dataclass` classes that serve as the typed interface between the `Database` class and the rest of the application. Each model provides `to_dict()` for serialization (datetime fields become ISO-format strings, lists become JSON arrays) and a `from_dict()` classmethod for deserialization (handles raw dicts from `sqlite3.Row` as well as pre-parsed dicts). Models with datetime fields accept ISO strings, Unix timestamps, or `None` (falls back to `datetime.now()`). List fields stored as JSON strings in SQLite (e.g., tags, favorite_markets) are transparently parsed in `from_dict()`.

## Common Patterns

- **All models** have `to_dict() -> Dict[str, Any]` and `@classmethod from_dict(cls, data) -> Self`.
- **Datetime handling**: `from_dict()` checks if the value is a `str` (parses via `fromisoformat`), `int`/`float` (treats as Unix timestamp where applicable), or `None` (defaults to `datetime.now()`).
- **JSON list fields**: `tags`, `favorite_markets`, and `data` are stored as JSON text in SQLite. `from_dict()` calls `json.loads()` if the value is a string, passes through if already a list/dict.
- **Optional IDs**: Models with auto-increment primary keys use `id: Optional[int] = None`. The database assigns the ID on insert.

## Model Reference

### Wallet

Wallet profile for tracking traders. Primary entity in the whale tracking and copy trading systems.

```python
@dataclass
class Wallet:
    address: str                              # Wallet address (PK in DB)
    first_seen: datetime                      # When first observed
    total_trades: int = 0                     # Lifetime trade count
    total_volume: float = 0.0                 # Lifetime volume in USD
    win_rate: float = 0.0                     # 0.0 to 1.0
    avg_position_size: float = 0.0            # Average trade notional
    tags: List[str] = field(default_factory=list)  # e.g., ["whale", "followed"]
    updated_at: datetime = field(default_factory=datetime.now)

    # Analytics fields
    total_wins: int = 0
    total_losses: int = 0
    largest_trade: float = 0.0                # Largest single trade in USD
    favorite_markets: List[str] = field(default_factory=list)  # Top market IDs
    risk_score: int = 0                       # 0-100, higher = more suspicious
```

**Classification methods:**

| Method | Criteria | Used By |
|--------|----------|---------|
| `is_whale()` | `total_volume >= 100,000` OR `"whale"` in tags | Whale tracker, dashboard |
| `is_smart_money()` | `win_rate >= 0.70` AND `total_trades >= 10` | Prediction signals |
| `is_suspicious()` | `risk_score >= 70` OR `"insider_suspect"` in tags | Insider detection |

**Tag conventions:**

| Tag | Meaning | Set By |
|-----|---------|--------|
| `"whale"` | High-volume trader | Whale tracker |
| `"followed"` | User is copy-trading this wallet | `follow_wallet()` / `unfollow_wallet()` |
| `"insider_suspect"` | Flagged by insider detection | `InsiderDetector` |

**Example:**

```python
from polyterm.db.models import Wallet
from datetime import datetime

wallet = Wallet(
    address="0xabc123...",
    first_seen=datetime(2024, 1, 15),
    total_volume=250000.0,
    win_rate=0.78,
    total_trades=45,
    tags=["whale", "followed"],
    risk_score=25,
)

wallet.is_whale()       # True (volume >= 100k)
wallet.is_smart_money() # True (win_rate >= 0.70 and trades >= 10)
wallet.is_suspicious()  # False (risk_score < 70)

d = wallet.to_dict()    # All fields serialized, datetimes as ISO strings
wallet2 = Wallet.from_dict(d)  # Round-trip reconstruction
```

### Trade

Individual trade record. Represents a single fill on a prediction market.

```python
@dataclass
class Trade:
    id: Optional[int] = None            # Auto-assigned by DB
    market_id: str = ""                  # Condition/market ID
    market_slug: str = ""                # URL-friendly slug
    wallet_address: str = ""             # Trader address (FK to wallets)
    side: str = ""                       # "BUY" or "SELL"
    outcome: str = ""                    # "YES" or "NO"
    price: float = 0.0                   # Per-share price (0.0 - 1.0)
    size: float = 0.0                    # Number of shares
    notional: float = 0.0               # price * size (USD value)
    timestamp: datetime = field(default_factory=datetime.now)
    tx_hash: str = ""                    # On-chain transaction hash
    maker_address: str = ""              # Order maker
    taker_address: str = ""              # Order taker
```

**Timestamp parsing**: `from_dict()` accepts ISO strings, Unix timestamps (int/float), or None.

**Example:**

```python
from polyterm.db.models import Trade

# From a CLOB WebSocket trade event
trade = Trade.from_dict({
    "market_id": "0xmarket...",
    "wallet_address": "0xtrader...",
    "side": "BUY",
    "outcome": "YES",
    "price": 0.65,
    "size": 1000,
    "notional": 650.0,
    "timestamp": 1704067200,  # Unix timestamp accepted
    "tx_hash": "0xtx...",
})
```

### Alert

Alert record for whale activity, insider detection, arbitrage, price shifts, and volume spikes.

```python
@dataclass
class Alert:
    id: Optional[int] = None
    alert_type: str = ""                 # whale, insider, arbitrage, price_shift, volume_spike
    market_id: str = ""
    wallet_address: str = ""
    severity: int = 0                    # 0-100
    message: str = ""                    # Human-readable description
    data: Dict[str, Any] = field(default_factory=dict)  # Arbitrary metadata
    created_at: datetime = field(default_factory=datetime.now)
    acknowledged: bool = False
```

**Severity mapping**: `from_dict()` converts string severity labels to numeric values when the source provides strings instead of integers:

| Label | Numeric Value |
|-------|---------------|
| critical | 90 |
| high | 80 |
| medium | 50 |
| low | 20 |

**Example:**

```python
from polyterm.db.models import Alert

alert = Alert(
    alert_type="whale",
    market_id="0xmarket...",
    wallet_address="0xwhale...",
    severity=80,
    message="Whale bought 50,000 YES shares at $0.42",
    data={"notional": 21000, "side": "BUY", "outcome": "YES"},
)

# String severity is auto-converted
alert2 = Alert.from_dict({"severity": "critical", "message": "..."})
assert alert2.severity == 90
```

### MarketSnapshot

Point-in-time market data for historical analysis and chart rendering.

```python
@dataclass
class MarketSnapshot:
    id: Optional[int] = None
    market_id: str = ""
    market_slug: str = ""
    title: str = ""
    probability: float = 0.0            # Current YES probability (0.0 - 1.0)
    volume_24h: float = 0.0             # 24-hour volume in USD
    liquidity: float = 0.0              # Total liquidity in USD
    best_bid: float = 0.0
    best_ask: float = 0.0
    spread: float = 0.0                 # best_ask - best_bid
    timestamp: datetime = field(default_factory=datetime.now)
```

**Example:**

```python
from polyterm.db.models import MarketSnapshot

snapshot = MarketSnapshot(
    market_id="0xmarket...",
    market_slug="will-btc-hit-100k",
    title="Will BTC hit $100k?",
    probability=0.65,
    volume_24h=1250000.0,
    liquidity=340000.0,
    best_bid=0.64,
    best_ask=0.66,
    spread=0.02,
)
```

### ResolutionOutcome

Market resolution data for tracking settlement. Captured from CLOB WebSocket `market_resolved` events or fetched from REST APIs.

```python
@dataclass
class ResolutionOutcome:
    id: Optional[int] = None
    market_id: str = ""
    market_slug: str = ""
    title: str = ""
    resolved: bool = False
    outcome: str = ""                    # "YES", "NO", or "" if unresolved
    winning_price: float = 0.0           # Final price (1.0 for resolved winner)
    resolved_at: Optional[datetime] = None
    resolution_source: str = ""          # e.g., "UMA oracle"
    closed_at: Optional[datetime] = None # When market stopped trading
    fetched_at: datetime = field(default_factory=datetime.now)
```

**Property:**

| Property | Returns |
|----------|---------|
| `status` | `"Resolved: YES"` / `"Resolved: NO"` if resolved; `"Pending resolution"` if closed but not resolved; `"Active"` otherwise |

**Example:**

```python
from polyterm.db.models import ResolutionOutcome
from datetime import datetime

res = ResolutionOutcome(
    market_id="0xmarket...",
    title="Will BTC hit $100k by Dec 2025?",
    resolved=True,
    outcome="YES",
    winning_price=1.0,
    resolved_at=datetime(2025, 11, 20, 14, 30),
    resolution_source="UMA oracle",
)

res.status  # "Resolved: YES"

# Pending state
pending = ResolutionOutcome(
    market_id="0xother...",
    closed_at=datetime(2025, 12, 1),
)
pending.status  # "Pending resolution"
```

### ArbitrageOpportunity

Record of a detected arbitrage opportunity between two markets.

```python
@dataclass
class ArbitrageOpportunity:
    id: Optional[int] = None
    market1_id: str = ""
    market2_id: str = ""
    market1_title: str = ""
    market2_title: str = ""
    market1_price: float = 0.0
    market2_price: float = 0.0
    spread: float = 0.0                 # Price gap
    expected_profit: float = 0.0        # Expected profit per dollar
    timestamp: datetime = field(default_factory=datetime.now)
    status: str = "open"                # open, closed, or expired
```

**Status lifecycle**: `open` -> `closed` (if executed or spread disappears) or `open` -> `expired` (if opportunity aged out). The `Database.cleanup_old_data()` method prunes non-open records older than 30 days.

**Example:**

```python
from polyterm.db.models import ArbitrageOpportunity

arb = ArbitrageOpportunity(
    market1_id="0xmarket_a...",
    market2_id="0xmarket_b...",
    market1_title="Will X happen? (YES)",
    market2_title="Will X happen? (NO)",
    market1_price=0.45,
    market2_price=0.50,
    spread=0.05,
    expected_profit=0.05,
    status="open",
)
```

## Serialization Round-Trip

All models support lossless round-trip serialization:

```python
original = Wallet(address="0xabc...", first_seen=datetime.now())
data = original.to_dict()        # dict with ISO strings
restored = Wallet.from_dict(data) # reconstructed Wallet
```

This works whether `data` comes from `to_dict()`, a `sqlite3.Row` converted to dict, or a JSON-parsed API response. The `from_dict()` methods are deliberately lenient: missing keys fall back to defaults, and type coercion handles strings, numbers, and None values gracefully.

## Related Features

- **Database**: See [database.md](database.md) for the `Database` class that persists these models in SQLite.
- **Whale Tracker** (`core/whale_tracker.py`): Creates `Wallet` and `Trade` instances from CLOB WebSocket events and REST data.
- **Insider Detection** (`core/whale_tracker.py` -- `InsiderDetector`): Scores wallets and sets `risk_score` on `Wallet` models.
- **Arbitrage Scanner** (`core/arbitrage.py`): Produces `ArbitrageOpportunity` records.
- **Live Order Book** (`core/orderbook.py`): Generates `ResolutionOutcome` records from `market_resolved` WebSocket events.
- **JSON Output** (`utils/json_output.py`): Uses `to_dict()` for `--format json` serialization across all CLI commands.
