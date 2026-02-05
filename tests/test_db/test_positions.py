"""Tests for position tracking and P&L calculation"""

import pytest
import tempfile
import os
from datetime import datetime

from polyterm.db.database import Database


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "test.db")
        db = Database(db_path)
        yield db


class TestPositionPnL:
    """Test position P&L calculations including side awareness"""

    def test_yes_position_profit(self, temp_db):
        """YES position profits when price rises"""
        pos_id = temp_db.add_position("m1", "Test Market", "yes", 100, 0.40)
        temp_db.close_position(pos_id, 0.70)

        summary = temp_db.get_position_summary()
        assert summary['realized_pnl'] > 0  # Should be profitable
        assert summary['wins'] == 1
        assert summary['losses'] == 0

    def test_yes_position_loss(self, temp_db):
        """YES position loses when price falls"""
        pos_id = temp_db.add_position("m1", "Test Market", "yes", 100, 0.70)
        temp_db.close_position(pos_id, 0.40)

        summary = temp_db.get_position_summary()
        assert summary['realized_pnl'] < 0
        assert summary['wins'] == 0
        assert summary['losses'] == 1

    def test_no_position_profit(self, temp_db):
        """NO position profits when price falls"""
        pos_id = temp_db.add_position("m1", "Test Market", "no", 100, 0.70)
        temp_db.close_position(pos_id, 0.40)

        summary = temp_db.get_position_summary()
        # NO side: profit = (entry - exit) * shares = (0.70 - 0.40) * 100 = 30
        assert summary['realized_pnl'] > 0
        assert summary['wins'] == 1
        assert summary['losses'] == 0

    def test_no_position_loss(self, temp_db):
        """NO position loses when price rises"""
        pos_id = temp_db.add_position("m1", "Test Market", "no", 100, 0.40)
        temp_db.close_position(pos_id, 0.70)

        summary = temp_db.get_position_summary()
        # NO side: loss = (entry - exit) * shares = (0.40 - 0.70) * 100 = -30
        assert summary['realized_pnl'] < 0
        assert summary['wins'] == 0
        assert summary['losses'] == 1

    def test_mixed_positions(self, temp_db):
        """Mix of YES and NO positions calculated correctly"""
        # YES profit: (0.80 - 0.40) * 100 = 40
        pos1 = temp_db.add_position("m1", "Market 1", "yes", 100, 0.40)
        temp_db.close_position(pos1, 0.80)

        # NO profit: (0.60 - 0.30) * 100 = 30
        pos2 = temp_db.add_position("m2", "Market 2", "no", 100, 0.60)
        temp_db.close_position(pos2, 0.30)

        summary = temp_db.get_position_summary()
        assert summary['realized_pnl'] == pytest.approx(70.0, abs=0.01)
        assert summary['wins'] == 2
        assert summary['losses'] == 0

    def test_open_positions_not_in_pnl(self, temp_db):
        """Open positions should not affect realized P&L"""
        temp_db.add_position("m1", "Open Market", "yes", 100, 0.50)

        summary = temp_db.get_position_summary()
        assert summary['open_positions'] == 1
        assert summary['realized_pnl'] == 0
        assert summary['closed_positions'] == 0

    def test_win_rate_calculation(self, temp_db):
        """Win rate should account for both sides correctly"""
        # 2 wins, 1 loss
        p1 = temp_db.add_position("m1", "Win 1", "yes", 100, 0.30)
        temp_db.close_position(p1, 0.70)

        p2 = temp_db.add_position("m2", "Win 2", "no", 100, 0.70)
        temp_db.close_position(p2, 0.30)

        p3 = temp_db.add_position("m3", "Loss 1", "yes", 100, 0.70)
        temp_db.close_position(p3, 0.30)

        summary = temp_db.get_position_summary()
        assert summary['wins'] == 2
        assert summary['losses'] == 1
        assert summary['win_rate'] == pytest.approx(66.67, abs=0.1)


class TestScreenerPresets:
    """Test screener preset JSON handling"""

    def test_save_and_get_preset(self, temp_db):
        """Preset should save and retrieve correctly"""
        temp_db.save_screener_preset("test_preset", {"volume": 1000, "active": True})
        presets = temp_db.get_screener_presets()
        assert len(presets) == 1
        assert presets[0]['name'] == "test_preset"
        assert presets[0]['filters']['volume'] == 1000

    def test_corrupt_filter_json_handled(self, temp_db):
        """Corrupt JSON in filters should not crash"""
        # First save a valid preset
        temp_db.save_screener_preset("good", {"volume": 1000})

        # Corrupt the JSON directly in the database
        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE screener_presets SET filters = 'not-valid-json' WHERE name = 'good'"
            )

        # Should not crash, should return empty dict for filters
        presets = temp_db.get_screener_presets()
        assert len(presets) == 1
        assert presets[0]['filters'] == {}

    def test_get_single_preset_corrupt_json(self, temp_db):
        """Single preset with corrupt JSON should return empty filters"""
        temp_db.save_screener_preset("test", {"key": "value"})

        with temp_db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE screener_presets SET filters = '{broken' WHERE name = 'test'"
            )

        preset = temp_db.get_screener_preset("test")
        assert preset is not None
        assert preset['filters'] == {}
