"""Tests for SQLite database module"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta
from pathlib import Path

from polyterm.db.database import Database
from polyterm.db.models import Wallet, Trade, Alert, MarketSnapshot, ArbitrageOpportunity


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        yield db


class TestDatabase:
    """Test database operations"""

    def test_database_initialization(self, temp_db):
        """Test that database initializes correctly"""
        stats = temp_db.get_database_stats()
        assert 'wallets' in stats
        assert 'trades' in stats
        assert 'alerts' in stats
        assert 'market_snapshots' in stats
        assert stats['wallets'] == 0

    def test_wallet_operations(self, temp_db):
        """Test wallet CRUD operations"""
        # Create wallet
        wallet = Wallet(
            address="0x1234567890abcdef",
            first_seen=datetime.now(),
            total_trades=10,
            total_volume=50000.0,
            win_rate=0.75,
            tags=["whale", "smart_money"],
        )

        # Insert
        temp_db.upsert_wallet(wallet)

        # Read
        retrieved = temp_db.get_wallet("0x1234567890abcdef")
        assert retrieved is not None
        assert retrieved.address == wallet.address
        assert retrieved.total_trades == 10
        assert retrieved.total_volume == 50000.0
        assert "whale" in retrieved.tags

        # Update
        wallet.total_trades = 20
        wallet.total_volume = 100000.0
        temp_db.upsert_wallet(wallet)

        updated = temp_db.get_wallet("0x1234567890abcdef")
        assert updated.total_trades == 20
        assert updated.total_volume == 100000.0

    def test_wallet_tags(self, temp_db):
        """Test adding and removing wallet tags"""
        wallet = Wallet(
            address="0xtest",
            first_seen=datetime.now(),
        )
        temp_db.upsert_wallet(wallet)

        temp_db.add_wallet_tag("0xtest", "whale")
        retrieved = temp_db.get_wallet("0xtest")
        assert "whale" in retrieved.tags

        temp_db.remove_wallet_tag("0xtest", "whale")
        retrieved = temp_db.get_wallet("0xtest")
        assert "whale" not in retrieved.tags

    def test_whale_wallets(self, temp_db):
        """Test getting whale wallets"""
        # Create regular wallet
        regular = Wallet(
            address="0xregular",
            first_seen=datetime.now(),
            total_volume=1000.0,
        )
        temp_db.upsert_wallet(regular)

        # Create whale wallet
        whale = Wallet(
            address="0xwhale",
            first_seen=datetime.now(),
            total_volume=200000.0,
        )
        temp_db.upsert_wallet(whale)

        whales = temp_db.get_whale_wallets(min_volume=100000)
        assert len(whales) == 1
        assert whales[0].address == "0xwhale"

    def test_smart_money_wallets(self, temp_db):
        """Test getting smart money wallets"""
        # Create smart money wallet
        smart = Wallet(
            address="0xsmart",
            first_seen=datetime.now(),
            total_trades=20,
            win_rate=0.80,
        )
        temp_db.upsert_wallet(smart)

        # Create regular wallet
        regular = Wallet(
            address="0xregular",
            first_seen=datetime.now(),
            total_trades=5,
            win_rate=0.50,
        )
        temp_db.upsert_wallet(regular)

        smart_money = temp_db.get_smart_money_wallets()
        assert len(smart_money) == 1
        assert smart_money[0].address == "0xsmart"

    def test_trade_operations(self, temp_db):
        """Test trade CRUD operations"""
        # Create wallet first (foreign key constraint)
        wallet = Wallet(
            address="0xtrader",
            first_seen=datetime.now(),
            total_trades=0,
            total_volume=0,
            win_rate=0.0,
            avg_position_size=0,
        )
        temp_db.upsert_wallet(wallet)

        trade = Trade(
            market_id="market1",
            wallet_address="0xtrader",
            side="BUY",
            outcome="YES",
            price=0.65,
            size=1000,
            notional=650.0,
            timestamp=datetime.now(),
        )

        trade_id = temp_db.insert_trade(trade)
        assert trade_id > 0

        # Get by wallet
        trades = temp_db.get_trades_by_wallet("0xtrader")
        assert len(trades) == 1
        assert trades[0].market_id == "market1"

        # Get by market
        trades = temp_db.get_trades_by_market("market1")
        assert len(trades) == 1

    def test_large_trades(self, temp_db):
        """Test getting large (whale) trades"""
        # Create wallets first (foreign key constraint)
        for addr in ["0xsmall", "0xlarge"]:
            wallet = Wallet(
                address=addr,
                first_seen=datetime.now(),
                total_trades=0,
                total_volume=0,
                win_rate=0.0,
                avg_position_size=0,
            )
            temp_db.upsert_wallet(wallet)

        # Small trade
        small = Trade(
            market_id="market1",
            wallet_address="0xsmall",
            side="BUY",
            price=0.50,
            size=100,
            notional=50.0,
            timestamp=datetime.now(),
        )
        temp_db.insert_trade(small)

        # Large trade
        large = Trade(
            market_id="market1",
            wallet_address="0xlarge",
            side="BUY",
            price=0.50,
            size=50000,
            notional=25000.0,
            timestamp=datetime.now(),
        )
        temp_db.insert_trade(large)

        large_trades = temp_db.get_large_trades(min_notional=10000)
        assert len(large_trades) == 1
        assert large_trades[0].wallet_address == "0xlarge"

    def test_alert_operations(self, temp_db):
        """Test alert CRUD operations"""
        alert = Alert(
            alert_type="whale",
            market_id="market1",
            wallet_address="0xwhale",
            severity=80,
            message="Large trade detected",
            data={"notional": 50000},
        )

        alert_id = temp_db.insert_alert(alert)
        assert alert_id > 0

        # Get recent alerts
        alerts = temp_db.get_recent_alerts(limit=10)
        assert len(alerts) == 1
        assert alerts[0].alert_type == "whale"

        # Get unacknowledged
        unack = temp_db.get_unacknowledged_alerts()
        assert len(unack) == 1

        # Acknowledge
        temp_db.acknowledge_alert(alert_id)
        unack = temp_db.get_unacknowledged_alerts()
        assert len(unack) == 0

    def test_market_snapshot_operations(self, temp_db):
        """Test market snapshot operations"""
        snapshot = MarketSnapshot(
            market_id="market1",
            title="Test Market",
            probability=0.65,
            volume_24h=100000.0,
            liquidity=50000.0,
            best_bid=0.64,
            best_ask=0.66,
            spread=0.02,
            timestamp=datetime.now(),
        )

        snap_id = temp_db.insert_snapshot(snapshot)
        assert snap_id > 0

        # Get latest
        latest = temp_db.get_latest_snapshot("market1")
        assert latest is not None
        assert latest.probability == 0.65

        # Get history
        history = temp_db.get_market_history("market1")
        assert len(history) == 1

    def test_arbitrage_operations(self, temp_db):
        """Test arbitrage opportunity operations"""
        arb = ArbitrageOpportunity(
            market1_id="market1",
            market2_id="market2",
            market1_title="Market 1",
            market2_title="Market 2",
            market1_price=0.45,
            market2_price=0.52,
            spread=0.03,
            expected_profit=150.0,
            timestamp=datetime.now(),
        )

        arb_id = temp_db.insert_arbitrage(arb)
        assert arb_id > 0

        # Get open
        open_arbs = temp_db.get_open_arbitrage()
        assert len(open_arbs) == 1

        # Close
        temp_db.close_arbitrage(arb_id)
        open_arbs = temp_db.get_open_arbitrage()
        assert len(open_arbs) == 0

    def test_wallet_stats(self, temp_db):
        """Test comprehensive wallet statistics"""
        wallet = Wallet(
            address="0xtrader",
            first_seen=datetime.now(),
            total_trades=5,
            total_volume=10000.0,
        )
        temp_db.upsert_wallet(wallet)

        # Add some trades
        for i in range(5):
            trade = Trade(
                market_id=f"market{i % 2}",
                wallet_address="0xtrader",
                side="BUY",
                price=0.50,
                size=1000,
                notional=500.0,
                timestamp=datetime.now(),
            )
            temp_db.insert_trade(trade)

        stats = temp_db.get_wallet_stats("0xtrader")
        assert stats['wallet']['address'] == "0xtrader"
        assert len(stats['recent_trades']) == 5

    def test_cleanup_old_data(self, temp_db):
        """Test cleanup of old data"""
        # Add old snapshot
        old_snapshot = MarketSnapshot(
            market_id="market1",
            probability=0.50,
            timestamp=datetime.now() - timedelta(days=60),
        )
        temp_db.insert_snapshot(old_snapshot)

        # Add recent snapshot
        new_snapshot = MarketSnapshot(
            market_id="market1",
            probability=0.60,
            timestamp=datetime.now(),
        )
        temp_db.insert_snapshot(new_snapshot)

        deleted = temp_db.cleanup_old_data(days=30)
        assert deleted >= 1

        history = temp_db.get_market_history("market1", hours=24*365)
        assert len(history) == 1
        assert history[0].probability == 0.60


class TestWalletModel:
    """Test Wallet model methods"""

    def test_is_whale(self):
        """Test whale classification"""
        whale = Wallet(
            address="0x",
            first_seen=datetime.now(),
            total_volume=150000.0,
        )
        assert whale.is_whale()

        not_whale = Wallet(
            address="0x",
            first_seen=datetime.now(),
            total_volume=1000.0,
        )
        assert not not_whale.is_whale()

        # Tagged as whale
        tagged = Wallet(
            address="0x",
            first_seen=datetime.now(),
            total_volume=1000.0,
            tags=["whale"],
        )
        assert tagged.is_whale()

    def test_is_smart_money(self):
        """Test smart money classification"""
        smart = Wallet(
            address="0x",
            first_seen=datetime.now(),
            total_trades=20,
            win_rate=0.75,
        )
        assert smart.is_smart_money()

        not_smart = Wallet(
            address="0x",
            first_seen=datetime.now(),
            total_trades=5,
            win_rate=0.50,
        )
        assert not not_smart.is_smart_money()

    def test_is_suspicious(self):
        """Test suspicious classification"""
        suspicious = Wallet(
            address="0x",
            first_seen=datetime.now(),
            risk_score=80,
        )
        assert suspicious.is_suspicious()

        tagged_suspicious = Wallet(
            address="0x",
            first_seen=datetime.now(),
            risk_score=30,
            tags=["insider_suspect"],
        )
        assert tagged_suspicious.is_suspicious()

        clean = Wallet(
            address="0x",
            first_seen=datetime.now(),
            risk_score=20,
        )
        assert not clean.is_suspicious()

    def test_to_from_dict(self):
        """Test serialization"""
        wallet = Wallet(
            address="0xtest",
            first_seen=datetime.now(),
            total_trades=10,
            tags=["whale", "tracked"],
        )

        data = wallet.to_dict()
        restored = Wallet.from_dict(data)

        assert restored.address == wallet.address
        assert restored.total_trades == wallet.total_trades
        assert restored.tags == wallet.tags
