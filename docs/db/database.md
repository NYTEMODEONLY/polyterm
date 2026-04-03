# Database Manager (`polyterm/db/database.py`)

SQLite database manager providing persistent local storage for all PolyTerm data.

## Overview

The `Database` class wraps a SQLite database at `~/.polyterm/data.db`, providing typed CRUD operations for wallets, trades, alerts, market snapshots, bookmarks, positions, and more. Every operation runs through a context-managed connection that enables foreign keys, auto-commits on success, and rolls back on error. The database self-initializes its schema on first use and runs automatic cleanup when row counts exceed 10,000.

## Key Patterns

- **Location**: `~/.polyterm/data.db` (override via `db_path` constructor parameter)
- **Connection handling**: All operations use `_get_connection()`, a `@contextmanager` that opens a `sqlite3.connect()`, sets `row_factory = sqlite3.Row`, enables `PRAGMA foreign_keys = ON`, commits on clean exit, and rolls back on exception.
- **Schema auto-migration**: On init, the `positions` table is inspected via `PRAGMA table_info` and the `wallet_address` column is added with `ALTER TABLE` if missing.
- **Auto-cleanup**: `_auto_cleanup()` runs at init. If total rows across core tables exceed 10,000, it calls `cleanup_old_data(days=30)` to prune old snapshots, acknowledged alerts (7 days), and non-open arbitrage records.
- **Upsert pattern**: Wallets, bookmarks, recently viewed, market notes, screener presets, and resolutions all use `INSERT ... ON CONFLICT DO UPDATE` for idempotent writes.
- **Return conventions**: Insert methods return the new row ID (`cursor.lastrowid`). Update/delete methods return `bool` indicating whether any rows were affected. Query methods return model instances or `List[Dict[str, Any]]`.

## Schema

### Tables

#### `wallets`
Primary key: `address TEXT`. Stores trader profiles with analytics fields.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| address | TEXT | PK | Wallet address |
| first_seen | TIMESTAMP | NOT NULL | When first observed |
| total_trades | INTEGER | 0 | Lifetime trade count |
| total_volume | REAL | 0.0 | Lifetime volume in USD |
| win_rate | REAL | 0.0 | 0.0 - 1.0 |
| avg_position_size | REAL | 0.0 | Average trade size |
| tags | TEXT | '[]' | JSON array of strings (e.g., "whale", "followed", "insider_suspect") |
| updated_at | TIMESTAMP | NOT NULL | Last update time |
| total_wins | INTEGER | 0 | Winning trade count |
| total_losses | INTEGER | 0 | Losing trade count |
| largest_trade | REAL | 0.0 | Largest single trade in USD |
| favorite_markets | TEXT | '[]' | JSON array of market IDs |
| risk_score | INTEGER | 0 | 0-100 insider risk score |

#### `trades`
Auto-increment PK. Foreign key on `wallet_address -> wallets(address)`.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| market_id | TEXT | NOT NULL | |
| market_slug | TEXT | '' | URL slug |
| wallet_address | TEXT | NOT NULL | FK to wallets |
| side | TEXT | NOT NULL | BUY or SELL |
| outcome | TEXT | '' | YES or NO |
| price | REAL | NOT NULL | Per-share price |
| size | REAL | NOT NULL | Number of shares |
| notional | REAL | 0.0 | price * size |
| timestamp | TIMESTAMP | NOT NULL | |
| tx_hash | TEXT | '' | Transaction hash |
| maker_address | TEXT | '' | |
| taker_address | TEXT | '' | |

#### `alerts`
Auto-increment PK. General-purpose alert storage.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| alert_type | TEXT | NOT NULL | whale, insider, arbitrage, price_shift, volume_spike |
| market_id | TEXT | '' | |
| wallet_address | TEXT | '' | |
| severity | INTEGER | 0 | 0-100 |
| message | TEXT | NOT NULL | Human-readable description |
| data | TEXT | '{}' | JSON metadata blob |
| created_at | TIMESTAMP | NOT NULL | |
| acknowledged | INTEGER | 0 | 0 = unread, 1 = acknowledged |

#### `market_snapshots`
Auto-increment PK. Point-in-time market data for charts and history.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| market_id | TEXT | NOT NULL | |
| market_slug | TEXT | '' | |
| title | TEXT | '' | |
| probability | REAL | 0.0 | Current YES probability |
| volume_24h | REAL | 0.0 | |
| liquidity | REAL | 0.0 | |
| best_bid | REAL | 0.0 | |
| best_ask | REAL | 0.0 | |
| spread | REAL | 0.0 | best_ask - best_bid |
| timestamp | TIMESTAMP | NOT NULL | |

#### `arbitrage_opportunities`
Auto-increment PK. Detected arbitrage records.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| market1_id | TEXT | NOT NULL | |
| market2_id | TEXT | NOT NULL | |
| market1_title | TEXT | '' | |
| market2_title | TEXT | '' | |
| market1_price | REAL | 0.0 | |
| market2_price | REAL | 0.0 | |
| spread | REAL | 0.0 | |
| expected_profit | REAL | 0.0 | |
| timestamp | TIMESTAMP | NOT NULL | |
| status | TEXT | 'open' | open, closed, or expired |

#### `bookmarks`
Primary key: `market_id TEXT`. Saved favorite markets.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| market_id | TEXT | PK | |
| title | TEXT | NOT NULL | |
| category | TEXT | '' | |
| probability | REAL | 0.0 | Probability at bookmark time |
| created_at | TIMESTAMP | NOT NULL | |
| notes | TEXT | '' | User notes |

#### `recently_viewed`
Primary key: `market_id TEXT`. Auto-tracked market views, capped at 50 entries.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| market_id | TEXT | PK | |
| title | TEXT | NOT NULL | |
| probability | REAL | 0.0 | |
| viewed_at | TIMESTAMP | NOT NULL | |
| view_count | INTEGER | 1 | Incremented on each view |

#### `price_alerts`
Auto-increment PK. User-defined price target alerts.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| market_id | TEXT | NOT NULL | |
| title | TEXT | NOT NULL | |
| target_price | REAL | NOT NULL | Target probability |
| direction | TEXT | NOT NULL | "above" or "below" |
| created_at | TIMESTAMP | NOT NULL | |
| triggered_at | TIMESTAMP | NULL | When alert fired |
| triggered | INTEGER | 0 | 0 = active, 1 = triggered |
| notified | INTEGER | 0 | 0 = pending, 1 = user notified |
| notes | TEXT | '' | |

#### `positions`
Auto-increment PK. Manual position tracking (no wallet connection required).

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| market_id | TEXT | NOT NULL | |
| title | TEXT | NOT NULL | |
| side | TEXT | NOT NULL | YES or NO |
| shares | REAL | NOT NULL | |
| entry_price | REAL | NOT NULL | |
| entry_date | TIMESTAMP | NOT NULL | |
| exit_price | REAL | NULL | Set when closed |
| exit_date | TIMESTAMP | NULL | Set when closed |
| status | TEXT | 'open' | open or closed |
| platform | TEXT | 'polymarket' | |
| wallet_address | TEXT | '' | Added via migration |
| notes | TEXT | '' | |

#### `screener_presets`
Auto-increment PK. Name is UNIQUE. Saved search filter configurations.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| name | TEXT | NOT NULL UNIQUE | Preset name |
| filters | TEXT | NOT NULL | JSON filter object |
| created_at | TIMESTAMP | NOT NULL | |

#### `market_notes`
Primary key: `market_id TEXT`. Free-form notes attached to markets.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| market_id | TEXT | PK | |
| title | TEXT | NOT NULL | |
| notes | TEXT | NOT NULL | |
| created_at | TIMESTAMP | NOT NULL | |
| updated_at | TIMESTAMP | NOT NULL | |

#### `resolutions`
Auto-increment PK. `market_id` has a UNIQUE constraint. Tracks market settlement outcomes.

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| id | INTEGER | PK AUTO | |
| market_id | TEXT | NOT NULL UNIQUE | |
| market_slug | TEXT | '' | |
| title | TEXT | '' | |
| resolved | INTEGER | 0 | 0 = unresolved, 1 = resolved |
| outcome | TEXT | '' | YES or NO |
| winning_price | REAL | 0.0 | Final price (1.0 for resolved) |
| resolved_at | TIMESTAMP | NULL | |
| resolution_source | TEXT | '' | e.g., "UMA oracle" |
| closed_at | TIMESTAMP | NULL | When trading stopped |
| fetched_at | TIMESTAMP | NOT NULL | When data was retrieved |

### Indexes

**Single-column indexes:**

| Index | Table | Column(s) |
|-------|-------|-----------|
| idx_trades_wallet | trades | wallet_address |
| idx_trades_market | trades | market_id |
| idx_trades_timestamp | trades | timestamp |
| idx_alerts_type | alerts | alert_type |
| idx_alerts_created | alerts | created_at |
| idx_snapshots_market | market_snapshots | market_id |
| idx_snapshots_timestamp | market_snapshots | timestamp |
| idx_wallets_risk | wallets | risk_score |
| idx_bookmarks_created | bookmarks | created_at |
| idx_recently_viewed_at | recently_viewed | viewed_at |
| idx_price_alerts_market | price_alerts | market_id |
| idx_price_alerts_triggered | price_alerts | triggered |
| idx_positions_market | positions | market_id |
| idx_positions_status | positions | status |

**Compound indexes (common query patterns):**

| Index | Table | Column(s) |
|-------|-------|-----------|
| idx_trades_market_ts | trades | market_id, timestamp |
| idx_snapshots_market_ts | market_snapshots | market_id, timestamp |
| idx_price_alerts_created | price_alerts | created_at |
| idx_positions_entry | positions | entry_date |
| idx_alerts_ack | alerts | acknowledged |
| idx_positions_wallet | positions | wallet_address |
| idx_resolutions_resolved | resolutions | resolved |
| idx_resolutions_resolved_at | resolutions | resolved_at |

## Operations by Domain

### Wallet Operations

| Method | Description |
|--------|-------------|
| `upsert_wallet(wallet)` | Insert or update a wallet profile |
| `get_wallet(address)` | Get a single wallet by address |
| `get_all_wallets(limit, offset)` | List wallets ordered by volume DESC |
| `get_whale_wallets(min_volume=100000)` | Wallets with volume >= threshold or "whale" tag |
| `get_smart_money_wallets(min_win_rate, min_trades)` | High win-rate wallets |
| `get_suspicious_wallets(min_risk_score=70)` | High risk-score or "insider_suspect" tagged wallets |
| `add_wallet_tag(address, tag)` | Append a tag to a wallet's tag list |
| `remove_wallet_tag(address, tag)` | Remove a tag from a wallet |
| `get_followed_wallets()` | Wallets with the "followed" tag (copy trading) |
| `follow_wallet(address)` | Add "followed" tag (creates wallet if needed); returns False if already followed |
| `unfollow_wallet(address)` | Remove "followed" tag; returns False if not following |
| `is_following(address)` | Check if wallet has "followed" tag |
| `update_wallet_from_trades(address)` | Recompute wallet stats from stored trade history |

### Trade Operations

| Method | Description |
|--------|-------------|
| `insert_trade(trade)` | Insert a trade record; returns new ID |
| `get_trades_by_wallet(address, limit, offset)` | Trades for a wallet, newest first |
| `get_trades_by_market(market_id, limit, offset)` | Trades for a market, newest first |
| `get_recent_trades(hours=24, limit=1000)` | Trades within a time window |
| `get_large_trades(min_notional=10000, hours=24)` | Whale trades above a notional threshold |

### Alert Operations

| Method | Description |
|--------|-------------|
| `insert_alert(alert)` | Insert an alert; returns new ID |
| `get_recent_alerts(limit, alert_type=None)` | Recent alerts, optionally filtered by type |
| `get_unacknowledged_alerts(limit=50)` | Unread alerts sorted by severity DESC |
| `acknowledge_alert(alert_id)` | Mark an alert as acknowledged |

### Snapshot Operations

| Method | Description |
|--------|-------------|
| `insert_snapshot(snapshot)` | Insert a point-in-time market snapshot |
| `get_market_history(market_id, hours, limit)` | Snapshots for a market within a time window |
| `get_latest_snapshot(market_id)` | Most recent snapshot for a market |

### Arbitrage Operations

| Method | Description |
|--------|-------------|
| `insert_arbitrage(arb)` | Insert an arbitrage opportunity; returns new ID |
| `get_open_arbitrage()` | All open opportunities, ordered by expected profit DESC |
| `close_arbitrage(arb_id, status='closed')` | Set status to closed or expired |

### Bookmark Operations

| Method | Description |
|--------|-------------|
| `bookmark_market(market_id, title, ...)` | Save a market bookmark (upsert) |
| `remove_bookmark(market_id)` | Delete a bookmark |
| `is_bookmarked(market_id)` | Check if a market is bookmarked |
| `get_bookmarks()` | All bookmarks, newest first |
| `get_bookmark(market_id)` | Single bookmark by market ID |
| `update_bookmark_notes(market_id, notes)` | Update notes on an existing bookmark |

### Recently Viewed Operations

| Method | Description |
|--------|-------------|
| `track_market_view(market_id, title, probability)` | Record a view (upsert, increments count, caps at 50 entries) |
| `get_recently_viewed(limit=20)` | Most recently viewed markets |
| `get_most_viewed(limit=10)` | Most frequently viewed markets |
| `clear_recent_history()` | Delete all recently viewed records |

### Price Alert Operations

| Method | Description |
|--------|-------------|
| `add_price_alert(market_id, title, target_price, direction, notes)` | Create alert; returns new ID |
| `get_price_alerts(active_only=True)` | List alerts (active-only or all) |
| `get_price_alert(alert_id)` | Single alert by ID |
| `remove_price_alert(alert_id)` | Delete an alert |
| `trigger_price_alert(alert_id)` | Mark as triggered with current timestamp |
| `mark_price_alert_notified(alert_id)` | Mark as notified |
| `get_alerts_for_market(market_id)` | Active alerts for a specific market |

### Position Operations

| Method | Description |
|--------|-------------|
| `add_position(market_id, title, side, shares, entry_price, ...)` | Open a tracked position; returns new ID |
| `get_positions(status=None, wallet_address=None)` | List positions with optional filters |
| `get_position(position_id)` | Single position by ID |
| `close_position(position_id, exit_price, status='closed')` | Close with exit price and timestamp |
| `delete_position(position_id)` | Delete a position record |
| `get_position_summary()` | Aggregate stats: open count/value, closed count, realized P&L, win/loss/win rate |

### Preset Operations

| Method | Description |
|--------|-------------|
| `save_screener_preset(name, filters)` | Save a named filter preset (upsert by name) |
| `get_screener_presets()` | All presets, ordered by name; filters are parsed from JSON |
| `get_screener_preset(name)` | Single preset by name |
| `delete_screener_preset(name)` | Delete a preset |

### Notes Operations

| Method | Description |
|--------|-------------|
| `set_market_note(market_id, title, notes)` | Create or update notes for a market |
| `get_market_note(market_id)` | Get notes for a single market |
| `get_all_market_notes()` | All notes, most recently updated first |
| `delete_market_note(market_id)` | Delete notes for a market |

### Resolution Operations

| Method | Description |
|--------|-------------|
| `save_resolution(resolution)` | Upsert resolution outcome by market_id |
| `get_resolution(market_id)` | Get resolution data for a market |
| `get_recent_resolutions(limit=20)` | Recently resolved markets |

### Analytics & Maintenance

| Method | Description |
|--------|-------------|
| `get_wallet_stats(address)` | Comprehensive wallet stats (profile + recent trades + top markets + 24h activity) |
| `get_database_stats()` | Row counts for wallets, trades, alerts, market_snapshots, arbitrage_opportunities |
| `cleanup_old_data(days=30)` | Prune snapshots older than N days, acknowledged alerts older than 7 days, non-open arbs |

## Usage Examples

### Basic Initialization

```python
from polyterm.db.database import Database

# Default location (~/.polyterm/data.db)
db = Database()

# Custom path (useful for testing)
db = Database(db_path="/tmp/test.db")
```

### Tracking a Wallet and Its Trades

```python
from polyterm.db.models import Wallet, Trade
from datetime import datetime

# Create and store a wallet
wallet = Wallet(
    address="0xabc123...",
    first_seen=datetime.now(),
    total_volume=250000.0,
    tags=["whale"],
)
db.upsert_wallet(wallet)

# Record a trade
trade = Trade(
    market_id="0xmarket...",
    market_slug="will-btc-hit-100k",
    wallet_address="0xabc123...",
    side="BUY",
    outcome="YES",
    price=0.65,
    size=1000,
    notional=650.0,
    timestamp=datetime.now(),
)
db.insert_trade(trade)

# Query whale trades in the last 24 hours
large_trades = db.get_large_trades(min_notional=10000, hours=24)
```

### Working with Bookmarks and Recently Viewed

```python
# Bookmark a market
db.bookmark_market(
    market_id="0xmarket...",
    title="Will BTC hit $100k?",
    category="Crypto",
    probability=0.65,
    notes="Watching for breakout",
)

# Track a view (auto-increments count, auto-prunes to 50)
db.track_market_view("0xmarket...", "Will BTC hit $100k?", 0.65)

# Get most frequently visited markets
top_markets = db.get_most_viewed(limit=5)
```

### Position Tracking with P&L

```python
# Open a position
pos_id = db.add_position(
    market_id="0xmarket...",
    title="Will BTC hit $100k?",
    side="YES",
    shares=500,
    entry_price=0.60,
)

# Close it later
db.close_position(pos_id, exit_price=0.85)

# Get portfolio summary
summary = db.get_position_summary()
# Returns: {open_positions, open_value, closed_positions, realized_pnl, wins, losses, win_rate}
```

### Price Alerts

```python
# Set an alert
alert_id = db.add_price_alert(
    market_id="0xmarket...",
    title="Will BTC hit $100k?",
    target_price=0.80,
    direction="above",
    notes="Consider selling",
)

# Check and trigger
alerts = db.get_alerts_for_market("0xmarket...")
db.trigger_price_alert(alert_id)
```

### Copy Trading (Follow Wallets)

```python
# Follow a wallet
db.follow_wallet("0xwhale...")

# List followed wallets
followed = db.get_followed_wallets()

# Check if following
is_following = db.is_following("0xwhale...")

# Unfollow
db.unfollow_wallet("0xwhale...")
```

### Database Maintenance

```python
# Check database size
stats = db.get_database_stats()
# Returns: {'wallets': 42, 'trades': 8500, 'alerts': 200, ...}

# Manual cleanup (auto-cleanup runs on init when >10k rows)
deleted_count = db.cleanup_old_data(days=14)
```

## Related Features

- **Models**: See [models.md](models.md) for the dataclass definitions used by `Database` methods.
- **Copy Trading**: The `follow_wallet` / `unfollow_wallet` methods power the `polyterm follow` command (`cli/commands/follow.py`).
- **Bookmarks**: Stored here, surfaced by `polyterm bookmarks` (`cli/commands/bookmarks.py`).
- **Price Charts**: `get_market_history()` provides fallback data for `polyterm chart` when CLOB price history is unavailable.
- **Dashboard**: `polyterm dashboard` reads bookmarks, alerts, followed wallets, and positions from this database.
- **Position Tracking**: P&L calculations in `get_position_summary()` account for side direction (YES profits when price rises, NO profits when price falls).
- **Real-Time Settlement**: The `resolutions` table stores outcomes detected via CLOB WebSocket `market_resolved` events (see `core/orderbook.py` and `api/clob.py`).
