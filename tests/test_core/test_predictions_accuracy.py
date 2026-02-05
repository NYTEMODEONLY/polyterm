"""Tests for prediction accuracy and momentum calculation fixes"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime

from polyterm.core.predictions import (
    PredictionEngine,
    Signal,
    SignalType,
    Direction,
)


class TestMomentumSignal:
    """Test momentum signal calculation edge cases"""

    def test_small_dataset_no_self_comparison(self):
        """Momentum with 5-7 datapoints should not compare price to itself"""
        engine = PredictionEngine.__new__(PredictionEngine)
        engine.db = MagicMock()
        engine.weights = {
            SignalType.MOMENTUM: 0.30,
            SignalType.VOLUME: 0.20,
            SignalType.WHALE: 0.15,
            SignalType.SMART_MONEY: 0.15,
            SignalType.TECHNICAL: 0.10,
            SignalType.ORDERBOOK: 0.10,
        }

        # Create 5 snapshots with clear upward trend
        snapshots = []
        for i in range(5):
            snap = MagicMock()
            snap.timestamp = 1000 + i * 3600
            snap.probability = 0.50 + i * 0.05  # 0.50, 0.55, 0.60, 0.65, 0.70
            snapshots.append(snap)

        engine.db.get_market_history = MagicMock(return_value=snapshots)

        signal = engine._calculate_momentum_signal("test_market")

        # Should detect upward momentum (not zero from self-comparison)
        assert signal is not None
        assert signal.direction == Direction.BULLISH

    def test_minimum_lookback_of_two(self):
        """recent_count should be at least 2 to avoid self-comparison"""
        engine = PredictionEngine.__new__(PredictionEngine)
        engine.db = MagicMock()
        engine.weights = {
            SignalType.MOMENTUM: 0.30,
            SignalType.VOLUME: 0.20,
            SignalType.WHALE: 0.15,
            SignalType.SMART_MONEY: 0.15,
            SignalType.TECHNICAL: 0.10,
            SignalType.ORDERBOOK: 0.10,
        }

        # 5 prices: len(prices)//4 = 1, but max(2, 1) = 2
        snapshots = []
        for i in range(5):
            snap = MagicMock()
            snap.timestamp = 1000 + i * 3600
            snap.probability = 0.40 + i * 0.10  # Significant uptrend
            snapshots.append(snap)

        engine.db.get_market_history = MagicMock(return_value=snapshots)

        signal = engine._calculate_momentum_signal("test_market")
        # With min lookback of 2: prices[-1] - prices[-2] = 0.80 - 0.70 = 0.10
        # This should produce a non-zero short_term_change
        assert signal is not None


class TestRecordOutcome:
    """Test prediction accuracy tracking"""

    def test_neutral_threshold_tighter(self):
        """Neutral/correct threshold should be 0.5, not 1.0"""
        engine = PredictionEngine.__new__(PredictionEngine)
        engine.accuracy_history = []

        # Create a prediction with small predicted change
        prediction = MagicMock()
        prediction.probability_change = 0.8  # Predicted +0.8% change
        prediction.direction = MagicMock()
        prediction.direction.value = "bullish"
        prediction.market_id = "test"

        # Actual change is -0.8% (opposite direction)
        # With old threshold (<1): both < 1, marked correct (WRONG)
        # With new threshold (<0.5): both NOT < 0.5, must match direction
        engine.record_outcome(prediction, -0.8)

        # Should be marked INCORRECT (predicted up 0.8, actual down 0.8)
        assert engine.accuracy_history[-1]['correct'] is False

    def test_truly_neutral_is_correct(self):
        """Very small prediction + very small actual = correct"""
        engine = PredictionEngine.__new__(PredictionEngine)
        engine.accuracy_history = []

        prediction = MagicMock()
        prediction.probability_change = 0.2  # Tiny predicted change
        prediction.direction = MagicMock()
        prediction.direction.value = "neutral"
        prediction.market_id = "test"

        engine.record_outcome(prediction, 0.1)  # Tiny actual change

        assert engine.accuracy_history[-1]['correct'] is True


class TestMomentumDescription:
    """Test momentum signal description formatting"""

    def test_zero_day_change_included(self):
        """A day change of exactly 0.0 should still appear in description"""
        engine = PredictionEngine.__new__(PredictionEngine)
        engine.weights = {
            SignalType.MOMENTUM: 0.30,
            SignalType.VOLUME: 0.20,
            SignalType.WHALE: 0.15,
            SignalType.SMART_MONEY: 0.15,
            SignalType.TECHNICAL: 0.10,
            SignalType.ORDERBOOK: 0.10,
        }

        # Mock market data with zero day change
        market_data = {
            'oneDayPriceChange': '0.0',
            'oneWeekPriceChange': '0.05',
            'oneMonthPriceChange': None,
        }

        signal = engine._calculate_momentum_signal_from_api(market_data)
        assert signal is not None
        # With `is not None` check, 0.0 should be included in description
        assert "1d:" in signal.description
