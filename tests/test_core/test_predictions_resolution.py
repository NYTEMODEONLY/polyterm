"""Tests for prediction verification with resolution outcomes"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime

from polyterm.core.predictions import (
    PredictionEngine,
    Prediction,
    Signal,
    SignalType,
    Direction,
)
from polyterm.db.models import ResolutionOutcome


class TestVerifyWithResolution:
    """Test PredictionEngine.verify_with_resolution"""

    @pytest.fixture
    def engine(self):
        """Create a PredictionEngine without a real database"""
        eng = PredictionEngine.__new__(PredictionEngine)
        eng.db = MagicMock()
        eng.accuracy_history = []
        eng.weights = {
            SignalType.MOMENTUM: 0.25,
            SignalType.VOLUME: 0.15,
            SignalType.WHALE: 0.20,
            SignalType.SMART_MONEY: 0.25,
            SignalType.ORDERBOOK: 0.10,
            SignalType.TECHNICAL: 0.05,
        }
        return eng

    def _make_prediction(self, direction, market_id="test-market"):
        return Prediction(
            market_id=market_id,
            market_title="Test Market",
            direction=direction,
            probability_change=5.0 if direction == Direction.BULLISH else -5.0,
            confidence=0.7,
            horizon_hours=24,
            signals=[],
            created_at=datetime(2026, 3, 1, 12, 0),
        )

    def test_bullish_prediction_yes_resolution_correct(self, engine):
        """Bullish prediction + YES resolution = correct"""
        prediction = self._make_prediction(Direction.BULLISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="YES",
            resolved_at=datetime(2026, 3, 15),
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record is not None
        assert record['correct'] is True
        assert record['actual_outcome'] == "YES"

    def test_bearish_prediction_no_resolution_correct(self, engine):
        """Bearish prediction + NO resolution = correct"""
        prediction = self._make_prediction(Direction.BEARISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="NO",
            resolved_at=datetime(2026, 3, 15),
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record is not None
        assert record['correct'] is True

    def test_bullish_prediction_no_resolution_incorrect(self, engine):
        """Bullish prediction + NO resolution = incorrect"""
        prediction = self._make_prediction(Direction.BULLISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="NO",
            resolved_at=datetime(2026, 3, 15),
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record is not None
        assert record['correct'] is False

    def test_bearish_prediction_yes_resolution_incorrect(self, engine):
        """Bearish prediction + YES resolution = incorrect"""
        prediction = self._make_prediction(Direction.BEARISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="YES",
            resolved_at=datetime(2026, 3, 15),
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record is not None
        assert record['correct'] is False

    def test_unresolved_returns_none(self, engine):
        """Unresolved market should return None"""
        prediction = self._make_prediction(Direction.BULLISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=False,
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record is None

    def test_record_appended_to_history(self, engine):
        """Verification should append to accuracy_history"""
        prediction = self._make_prediction(Direction.BULLISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="YES",
            resolved_at=datetime(2026, 3, 15),
        )
        assert len(engine.accuracy_history) == 0
        engine.verify_with_resolution(prediction, resolution)
        assert len(engine.accuracy_history) == 1

    def test_history_capped_at_1000(self, engine):
        """History should be capped at 1000 entries"""
        engine.accuracy_history = [{'dummy': i} for i in range(999)]
        prediction = self._make_prediction(Direction.BULLISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="YES",
            resolved_at=datetime(2026, 3, 15),
        )
        engine.verify_with_resolution(prediction, resolution)
        assert len(engine.accuracy_history) == 1000

        # One more should trim
        engine.verify_with_resolution(prediction, resolution)
        assert len(engine.accuracy_history) == 1000

    def test_record_includes_resolution_source(self, engine):
        """Record should include resolution metadata"""
        prediction = self._make_prediction(Direction.BULLISH)
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="YES",
            resolved_at=datetime(2026, 3, 15, 14, 30),
            resolution_source="UMA Oracle",
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record['resolution_source'] == "UMA Oracle"
        assert record['resolved_at'] == "2026-03-15T14:30:00"

    def test_neutral_prediction_yes_resolution_incorrect(self, engine):
        """Neutral prediction + YES resolution = incorrect"""
        prediction = self._make_prediction(Direction.NEUTRAL)
        prediction.probability_change = 0.0
        resolution = ResolutionOutcome(
            market_id="test-market",
            resolved=True,
            outcome="YES",
            resolved_at=datetime(2026, 3, 15),
        )
        record = engine.verify_with_resolution(prediction, resolution)
        assert record is not None
        assert record['correct'] is False
