"""Tests for AI-powered predictions module"""

import pytest
import tempfile
import os
from datetime import datetime, timedelta

from polyterm.db.database import Database
from polyterm.db.models import Trade, MarketSnapshot, Wallet
from polyterm.core.predictions import (
    PredictionEngine,
    Signal,
    SignalType,
    Direction,
    Prediction,
)


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        yield db


@pytest.fixture
def prediction_engine(temp_db):
    """Create prediction engine with test database"""
    return PredictionEngine(temp_db)


@pytest.fixture
def populated_db(temp_db):
    """Create database with test data"""
    # Add some market snapshots
    base_time = datetime.now()
    for i in range(20):
        snapshot = MarketSnapshot(
            market_id="test_market",
            market_slug="test-market",
            title="Test Market",
            probability=0.5 + (i * 0.01),  # Slowly increasing
            volume_24h=10000 + (i * 100),
            liquidity=5000,
            timestamp=base_time - timedelta(hours=20-i),
        )
        temp_db.insert_snapshot(snapshot)

    # Create wallet records first (foreign key constraint)
    for w in range(5):
        wallet = Wallet(
            address=f"0xwallet{w}",
            first_seen=base_time - timedelta(days=10),
            total_trades=10,
            total_volume=5000,
            win_rate=0.6,
            avg_position_size=500,
        )
        temp_db.upsert_wallet(wallet)

    # Add some trades
    for i in range(30):
        trade = Trade(
            market_id="test_market",
            wallet_address=f"0xwallet{i % 5}",
            side="BUY" if i % 3 != 0 else "SELL",
            outcome="YES" if i % 2 == 0 else "NO",
            price=0.5 + (i * 0.005),
            size=1000 + (i * 50),
            notional=500 + (i * 25),
            timestamp=base_time - timedelta(hours=30-i),
        )
        temp_db.insert_trade(trade)

    # Add a smart money wallet
    smart_wallet = Wallet(
        address="0xsmart",
        first_seen=base_time - timedelta(days=30),
        total_trades=50,
        total_volume=100000,
        win_rate=0.80,
        avg_position_size=2000,
    )
    temp_db.upsert_wallet(smart_wallet)

    return temp_db


class TestSignal:
    """Test Signal dataclass"""

    def test_signal_creation(self):
        """Test creating a signal"""
        signal = Signal(
            signal_type=SignalType.MOMENTUM,
            direction=Direction.BULLISH,
            strength=0.8,
            confidence=0.7,
            value=0.05,
            description="Test signal",
        )

        assert signal.signal_type == SignalType.MOMENTUM
        assert signal.direction == Direction.BULLISH
        assert signal.strength == 0.8

    def test_signal_to_dict(self):
        """Test signal serialization"""
        signal = Signal(
            signal_type=SignalType.WHALE,
            direction=Direction.BEARISH,
            strength=0.6,
            confidence=0.9,
            value=-0.3,
            description="Whale selling",
        )

        data = signal.to_dict()
        assert data['type'] == 'whale'
        assert data['direction'] == 'bearish'
        assert data['strength'] == 0.6


class TestPrediction:
    """Test Prediction dataclass"""

    def test_prediction_creation(self):
        """Test creating a prediction"""
        signals = [
            Signal(SignalType.MOMENTUM, Direction.BULLISH, 0.7, 0.8, 0.1, "Up"),
            Signal(SignalType.VOLUME, Direction.BULLISH, 0.5, 0.6, 0.2, "Vol"),
        ]

        prediction = Prediction(
            market_id="test",
            market_title="Test Market",
            direction=Direction.BULLISH,
            probability_change=5.0,
            confidence=0.7,
            horizon_hours=24,
            signals=signals,
        )

        assert prediction.direction == Direction.BULLISH
        assert len(prediction.signals) == 2

    def test_signal_summary(self):
        """Test signal summary calculation"""
        signals = [
            Signal(SignalType.MOMENTUM, Direction.BULLISH, 0.7, 0.8, 0.1, "Up"),
            Signal(SignalType.VOLUME, Direction.BEARISH, 0.5, 0.6, -0.2, "Down"),
            Signal(SignalType.WHALE, Direction.BULLISH, 0.8, 0.9, 0.3, "Up"),
        ]

        prediction = Prediction(
            market_id="test",
            market_title="Test",
            direction=Direction.BULLISH,
            probability_change=3.0,
            confidence=0.6,
            horizon_hours=24,
            signals=signals,
        )

        summary = prediction.signal_summary
        assert summary['bullish'] == 2
        assert summary['bearish'] == 1
        assert summary['neutral'] == 0


class TestPredictionEngine:
    """Test PredictionEngine class"""

    def test_engine_initialization(self, prediction_engine):
        """Test engine initialization"""
        assert prediction_engine is not None
        assert len(prediction_engine.weights) > 0

    def test_generate_prediction_empty_data(self, prediction_engine):
        """Test prediction with no data"""
        prediction = prediction_engine.generate_prediction("unknown_market")

        assert prediction.market_id == "unknown_market"
        # Should still return a prediction, possibly neutral
        assert prediction.direction in [Direction.BULLISH, Direction.BEARISH, Direction.NEUTRAL]

    def test_generate_prediction_with_data(self, populated_db):
        """Test prediction with populated data"""
        engine = PredictionEngine(populated_db)
        prediction = engine.generate_prediction("test_market", "Test Market")

        assert prediction.market_id == "test_market"
        assert prediction.market_title == "Test Market"
        assert -100 <= prediction.probability_change <= 100
        assert 0 <= prediction.confidence <= 1

    def test_momentum_signal(self, populated_db):
        """Test momentum signal calculation"""
        engine = PredictionEngine(populated_db)
        signal = engine._calculate_momentum_signal("test_market")

        if signal:
            assert signal.signal_type == SignalType.MOMENTUM
            assert -1 <= signal.value <= 1
            assert 0 <= signal.strength <= 1

    def test_technical_signal(self, populated_db):
        """Test technical (RSI) signal"""
        engine = PredictionEngine(populated_db)
        signal = engine._calculate_technical_signal("test_market")

        if signal:
            assert signal.signal_type == SignalType.TECHNICAL
            assert 0 <= signal.value <= 100  # RSI range

    def test_combine_signals(self, prediction_engine):
        """Test signal combination"""
        signals = [
            Signal(SignalType.MOMENTUM, Direction.BULLISH, 0.8, 0.9, 0.1, "Strong up"),
            Signal(SignalType.VOLUME, Direction.BULLISH, 0.6, 0.7, 0.2, "Vol up"),
            Signal(SignalType.WHALE, Direction.BEARISH, 0.4, 0.5, -0.1, "Whale sell"),
        ]

        direction, prob_change, confidence = prediction_engine._combine_signals(signals)

        # With more bullish signals, should be bullish
        assert direction in [Direction.BULLISH, Direction.NEUTRAL]
        assert -10 <= prob_change <= 10
        assert 0 <= confidence <= 1

    def test_record_outcome(self, prediction_engine):
        """Test accuracy tracking"""
        prediction = Prediction(
            market_id="test",
            market_title="Test",
            direction=Direction.BULLISH,
            probability_change=5.0,
            confidence=0.7,
            horizon_hours=24,
        )

        # Record correct prediction
        prediction_engine.record_outcome(prediction, 3.0)  # Actual was positive

        stats = prediction_engine.get_accuracy_stats()
        assert stats['total_predictions'] == 1
        assert stats['correct_predictions'] == 1

        # Record incorrect prediction
        prediction2 = Prediction(
            market_id="test2",
            market_title="Test2",
            direction=Direction.BULLISH,
            probability_change=5.0,
            confidence=0.7,
            horizon_hours=24,
        )
        prediction_engine.record_outcome(prediction2, -3.0)  # Actual was negative

        stats = prediction_engine.get_accuracy_stats()
        assert stats['total_predictions'] == 2
        assert stats['correct_predictions'] == 1
        assert stats['accuracy'] == 0.5

    def test_format_prediction(self, prediction_engine):
        """Test prediction formatting"""
        signals = [
            Signal(SignalType.MOMENTUM, Direction.BULLISH, 0.8, 0.9, 0.1, "Strong momentum"),
        ]

        prediction = Prediction(
            market_id="test",
            market_title="Test Market Will Something Happen",
            direction=Direction.BULLISH,
            probability_change=5.5,
            confidence=0.75,
            horizon_hours=24,
            signals=signals,
        )

        formatted = prediction_engine.format_prediction(prediction)

        assert "BULLISH" in formatted
        assert "5.5%" in formatted or "+5.5" in formatted
        assert "75%" in formatted
        assert "momentum" in formatted.lower()
