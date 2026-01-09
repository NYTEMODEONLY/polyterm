"""SQLite database manager for persistent storage"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

from .models import Wallet, Trade, Alert, MarketSnapshot, ArbitrageOpportunity


class Database:
    """SQLite database manager for PolyTerm persistent storage"""

    def __init__(self, db_path: Optional[str] = None):
        if db_path:
            self.db_path = Path(db_path)
        else:
            self.db_path = Path.home() / ".polyterm" / "data.db"

        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Wallets table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    address TEXT PRIMARY KEY,
                    first_seen TIMESTAMP NOT NULL,
                    total_trades INTEGER DEFAULT 0,
                    total_volume REAL DEFAULT 0.0,
                    win_rate REAL DEFAULT 0.0,
                    avg_position_size REAL DEFAULT 0.0,
                    tags TEXT DEFAULT '[]',
                    updated_at TIMESTAMP NOT NULL,
                    total_wins INTEGER DEFAULT 0,
                    total_losses INTEGER DEFAULT 0,
                    largest_trade REAL DEFAULT 0.0,
                    favorite_markets TEXT DEFAULT '[]',
                    risk_score INTEGER DEFAULT 0
                )
            """)

            # Trades table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    market_slug TEXT DEFAULT '',
                    wallet_address TEXT NOT NULL,
                    side TEXT NOT NULL,
                    outcome TEXT DEFAULT '',
                    price REAL NOT NULL,
                    size REAL NOT NULL,
                    notional REAL DEFAULT 0.0,
                    timestamp TIMESTAMP NOT NULL,
                    tx_hash TEXT DEFAULT '',
                    maker_address TEXT DEFAULT '',
                    taker_address TEXT DEFAULT '',
                    FOREIGN KEY (wallet_address) REFERENCES wallets(address)
                )
            """)

            # Alerts table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_type TEXT NOT NULL,
                    market_id TEXT DEFAULT '',
                    wallet_address TEXT DEFAULT '',
                    severity INTEGER DEFAULT 0,
                    message TEXT NOT NULL,
                    data TEXT DEFAULT '{}',
                    created_at TIMESTAMP NOT NULL,
                    acknowledged INTEGER DEFAULT 0
                )
            """)

            # Market snapshots table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS market_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market_id TEXT NOT NULL,
                    market_slug TEXT DEFAULT '',
                    title TEXT DEFAULT '',
                    probability REAL DEFAULT 0.0,
                    volume_24h REAL DEFAULT 0.0,
                    liquidity REAL DEFAULT 0.0,
                    best_bid REAL DEFAULT 0.0,
                    best_ask REAL DEFAULT 0.0,
                    spread REAL DEFAULT 0.0,
                    timestamp TIMESTAMP NOT NULL
                )
            """)

            # Arbitrage opportunities table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS arbitrage_opportunities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    market1_id TEXT NOT NULL,
                    market2_id TEXT NOT NULL,
                    market1_title TEXT DEFAULT '',
                    market2_title TEXT DEFAULT '',
                    market1_price REAL DEFAULT 0.0,
                    market2_price REAL DEFAULT 0.0,
                    spread REAL DEFAULT 0.0,
                    expected_profit REAL DEFAULT 0.0,
                    timestamp TIMESTAMP NOT NULL,
                    status TEXT DEFAULT 'open'
                )
            """)

            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet_address)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_market ON trades(market_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_trades_timestamp ON trades(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_type ON alerts(alert_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_alerts_created ON alerts(created_at)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_market ON market_snapshots(market_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_timestamp ON market_snapshots(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_wallets_risk ON wallets(risk_score)")

    # Wallet operations

    def upsert_wallet(self, wallet: Wallet) -> None:
        """Insert or update a wallet"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO wallets (
                    address, first_seen, total_trades, total_volume, win_rate,
                    avg_position_size, tags, updated_at, total_wins, total_losses,
                    largest_trade, favorite_markets, risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(address) DO UPDATE SET
                    total_trades = excluded.total_trades,
                    total_volume = excluded.total_volume,
                    win_rate = excluded.win_rate,
                    avg_position_size = excluded.avg_position_size,
                    tags = excluded.tags,
                    updated_at = excluded.updated_at,
                    total_wins = excluded.total_wins,
                    total_losses = excluded.total_losses,
                    largest_trade = excluded.largest_trade,
                    favorite_markets = excluded.favorite_markets,
                    risk_score = excluded.risk_score
            """, (
                wallet.address,
                wallet.first_seen.isoformat(),
                wallet.total_trades,
                wallet.total_volume,
                wallet.win_rate,
                wallet.avg_position_size,
                json.dumps(wallet.tags),
                wallet.updated_at.isoformat(),
                wallet.total_wins,
                wallet.total_losses,
                wallet.largest_trade,
                json.dumps(wallet.favorite_markets),
                wallet.risk_score,
            ))

    def get_wallet(self, address: str) -> Optional[Wallet]:
        """Get a wallet by address"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM wallets WHERE address = ?", (address,))
            row = cursor.fetchone()
            if row:
                return Wallet.from_dict(dict(row))
            return None

    def get_all_wallets(self, limit: int = 100, offset: int = 0) -> List[Wallet]:
        """Get all wallets"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM wallets ORDER BY total_volume DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
            return [Wallet.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_whale_wallets(self, min_volume: float = 100000) -> List[Wallet]:
        """Get wallets classified as whales"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wallets
                WHERE total_volume >= ? OR tags LIKE '%"whale"%'
                ORDER BY total_volume DESC
            """, (min_volume,))
            return [Wallet.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_smart_money_wallets(self, min_win_rate: float = 0.70, min_trades: int = 10) -> List[Wallet]:
        """Get wallets with high win rates (smart money)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wallets
                WHERE win_rate >= ? AND total_trades >= ?
                ORDER BY win_rate DESC, total_volume DESC
            """, (min_win_rate, min_trades))
            return [Wallet.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_suspicious_wallets(self, min_risk_score: int = 70) -> List[Wallet]:
        """Get wallets with high risk scores"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM wallets
                WHERE risk_score >= ? OR tags LIKE '%"insider_suspect"%'
                ORDER BY risk_score DESC
            """, (min_risk_score,))
            return [Wallet.from_dict(dict(row)) for row in cursor.fetchall()]

    def add_wallet_tag(self, address: str, tag: str) -> None:
        """Add a tag to a wallet"""
        wallet = self.get_wallet(address)
        if wallet and tag not in wallet.tags:
            wallet.tags.append(tag)
            wallet.updated_at = datetime.now()
            self.upsert_wallet(wallet)

    def remove_wallet_tag(self, address: str, tag: str) -> None:
        """Remove a tag from a wallet"""
        wallet = self.get_wallet(address)
        if wallet and tag in wallet.tags:
            wallet.tags.remove(tag)
            wallet.updated_at = datetime.now()
            self.upsert_wallet(wallet)

    # Trade operations

    def insert_trade(self, trade: Trade) -> int:
        """Insert a trade and return its ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    market_id, market_slug, wallet_address, side, outcome,
                    price, size, notional, timestamp, tx_hash,
                    maker_address, taker_address
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade.market_id,
                trade.market_slug,
                trade.wallet_address,
                trade.side,
                trade.outcome,
                trade.price,
                trade.size,
                trade.notional,
                trade.timestamp.isoformat(),
                trade.tx_hash,
                trade.maker_address,
                trade.taker_address,
            ))
            return cursor.lastrowid

    def get_trades_by_wallet(
        self,
        wallet_address: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trade]:
        """Get trades by wallet address"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE wallet_address = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (wallet_address, limit, offset))
            return [Trade.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_trades_by_market(
        self,
        market_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Trade]:
        """Get trades by market ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE market_id = ?
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (market_id, limit, offset))
            return [Trade.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_recent_trades(
        self,
        hours: int = 24,
        limit: int = 1000
    ) -> List[Trade]:
        """Get trades from the last N hours"""
        since = datetime.now() - timedelta(hours=hours)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (since.isoformat(), limit))
            return [Trade.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_large_trades(
        self,
        min_notional: float = 10000,
        hours: int = 24
    ) -> List[Trade]:
        """Get large trades (whale trades)"""
        since = datetime.now() - timedelta(hours=hours)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM trades
                WHERE notional >= ? AND timestamp >= ?
                ORDER BY notional DESC
            """, (min_notional, since.isoformat()))
            return [Trade.from_dict(dict(row)) for row in cursor.fetchall()]

    # Alert operations

    def insert_alert(self, alert: Alert) -> int:
        """Insert an alert and return its ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO alerts (
                    alert_type, market_id, wallet_address, severity,
                    message, data, created_at, acknowledged
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                alert.alert_type,
                alert.market_id,
                alert.wallet_address,
                alert.severity,
                alert.message,
                json.dumps(alert.data),
                alert.created_at.isoformat(),
                1 if alert.acknowledged else 0,
            ))
            return cursor.lastrowid

    def get_recent_alerts(
        self,
        limit: int = 100,
        alert_type: Optional[str] = None
    ) -> List[Alert]:
        """Get recent alerts"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if alert_type:
                cursor.execute("""
                    SELECT * FROM alerts
                    WHERE alert_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (alert_type, limit))
            else:
                cursor.execute("""
                    SELECT * FROM alerts
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            return [Alert.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_unacknowledged_alerts(self, limit: int = 50) -> List[Alert]:
        """Get unacknowledged alerts"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM alerts
                WHERE acknowledged = 0
                ORDER BY severity DESC, created_at DESC
                LIMIT ?
            """, (limit,))
            return [Alert.from_dict(dict(row)) for row in cursor.fetchall()]

    def acknowledge_alert(self, alert_id: int) -> None:
        """Mark an alert as acknowledged"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE alerts SET acknowledged = 1 WHERE id = ?",
                (alert_id,)
            )

    # Market snapshot operations

    def insert_snapshot(self, snapshot: MarketSnapshot) -> int:
        """Insert a market snapshot"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO market_snapshots (
                    market_id, market_slug, title, probability,
                    volume_24h, liquidity, best_bid, best_ask,
                    spread, timestamp
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                snapshot.market_id,
                snapshot.market_slug,
                snapshot.title,
                snapshot.probability,
                snapshot.volume_24h,
                snapshot.liquidity,
                snapshot.best_bid,
                snapshot.best_ask,
                snapshot.spread,
                snapshot.timestamp.isoformat(),
            ))
            return cursor.lastrowid

    def get_market_history(
        self,
        market_id: str,
        hours: int = 24,
        limit: int = 1000
    ) -> List[MarketSnapshot]:
        """Get market snapshot history"""
        since = datetime.now() - timedelta(hours=hours)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_snapshots
                WHERE market_id = ? AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (market_id, since.isoformat(), limit))
            return [MarketSnapshot.from_dict(dict(row)) for row in cursor.fetchall()]

    def get_latest_snapshot(self, market_id: str) -> Optional[MarketSnapshot]:
        """Get the latest snapshot for a market"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM market_snapshots
                WHERE market_id = ?
                ORDER BY timestamp DESC
                LIMIT 1
            """, (market_id,))
            row = cursor.fetchone()
            if row:
                return MarketSnapshot.from_dict(dict(row))
            return None

    # Arbitrage operations

    def insert_arbitrage(self, arb: ArbitrageOpportunity) -> int:
        """Insert an arbitrage opportunity"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO arbitrage_opportunities (
                    market1_id, market2_id, market1_title, market2_title,
                    market1_price, market2_price, spread, expected_profit,
                    timestamp, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                arb.market1_id,
                arb.market2_id,
                arb.market1_title,
                arb.market2_title,
                arb.market1_price,
                arb.market2_price,
                arb.spread,
                arb.expected_profit,
                arb.timestamp.isoformat(),
                arb.status,
            ))
            return cursor.lastrowid

    def get_open_arbitrage(self) -> List[ArbitrageOpportunity]:
        """Get open arbitrage opportunities"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM arbitrage_opportunities
                WHERE status = 'open'
                ORDER BY expected_profit DESC
            """)
            return [ArbitrageOpportunity.from_dict(dict(row)) for row in cursor.fetchall()]

    def close_arbitrage(self, arb_id: int, status: str = 'closed') -> None:
        """Close an arbitrage opportunity"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE arbitrage_opportunities SET status = ? WHERE id = ?",
                (status, arb_id)
            )

    # Analytics operations

    def get_wallet_stats(self, address: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a wallet"""
        wallet = self.get_wallet(address)
        if not wallet:
            return {}

        trades = self.get_trades_by_wallet(address, limit=1000)

        # Calculate additional stats
        markets = {}
        for trade in trades:
            if trade.market_id not in markets:
                markets[trade.market_id] = 0
            markets[trade.market_id] += trade.notional

        top_markets = sorted(markets.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            'wallet': wallet.to_dict(),
            'recent_trades': [t.to_dict() for t in trades[:20]],
            'top_markets': top_markets,
            'trade_count_24h': len([t for t in trades if t.timestamp > datetime.now() - timedelta(hours=24)]),
            'volume_24h': sum(t.notional for t in trades if t.timestamp > datetime.now() - timedelta(hours=24)),
        }

    def update_wallet_from_trades(self, address: str) -> None:
        """Update wallet statistics from trade history"""
        trades = self.get_trades_by_wallet(address, limit=10000)
        if not trades:
            return

        wallet = self.get_wallet(address)
        if not wallet:
            wallet = Wallet(
                address=address,
                first_seen=min(t.timestamp for t in trades),
            )

        wallet.total_trades = len(trades)
        wallet.total_volume = sum(t.notional for t in trades)
        wallet.avg_position_size = wallet.total_volume / wallet.total_trades if wallet.total_trades > 0 else 0
        wallet.largest_trade = max((t.notional for t in trades), default=0)

        # Track favorite markets
        market_volumes = {}
        for trade in trades:
            if trade.market_id not in market_volumes:
                market_volumes[trade.market_id] = 0
            market_volumes[trade.market_id] += trade.notional

        top_markets = sorted(market_volumes.items(), key=lambda x: x[1], reverse=True)[:5]
        wallet.favorite_markets = [m[0] for m in top_markets]

        wallet.updated_at = datetime.now()
        self.upsert_wallet(wallet)

    def cleanup_old_data(self, days: int = 30) -> int:
        """Clean up old data to prevent database bloat"""
        cutoff = datetime.now() - timedelta(days=days)
        deleted = 0

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Clean old snapshots (keep more recent)
            cursor.execute(
                "DELETE FROM market_snapshots WHERE timestamp < ?",
                (cutoff.isoformat(),)
            )
            deleted += cursor.rowcount

            # Clean old alerts (keep acknowledged ones for less time)
            ack_cutoff = datetime.now() - timedelta(days=7)
            cursor.execute(
                "DELETE FROM alerts WHERE created_at < ? AND acknowledged = 1",
                (ack_cutoff.isoformat(),)
            )
            deleted += cursor.rowcount

            # Clean expired arbitrage opportunities
            cursor.execute(
                "DELETE FROM arbitrage_opportunities WHERE timestamp < ? AND status != 'open'",
                (cutoff.isoformat(),)
            )
            deleted += cursor.rowcount

        return deleted

    def get_database_stats(self) -> Dict[str, int]:
        """Get database statistics"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            stats = {}

            for table in ['wallets', 'trades', 'alerts', 'market_snapshots', 'arbitrage_opportunities']:
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                stats[table] = cursor.fetchone()[0]

            return stats
