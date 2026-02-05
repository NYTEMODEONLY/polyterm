"""Tests for P&L streak calculation"""

import pytest


def _calculate_streak(pnls):
    """Reproduce the streak logic from pnl.py for testing"""
    current_streak = 0

    if pnls:
        last_pnl = pnls[-1]
        if last_pnl != 0:
            for p in reversed(pnls):
                if p == 0:
                    break
                if (p > 0) == (last_pnl > 0):
                    current_streak += 1 if last_pnl > 0 else -1
                else:
                    break

    return current_streak


class TestPnLStreak:
    """Test streak calculation edge cases"""

    def test_win_streak(self):
        """Consecutive wins produce positive streak"""
        assert _calculate_streak([10, 20, 30]) == 3

    def test_loss_streak(self):
        """Consecutive losses produce negative streak"""
        assert _calculate_streak([-10, -20, -30]) == -3

    def test_mixed_ends_with_win(self):
        """Mixed P&L ending with wins"""
        assert _calculate_streak([-10, -20, 10, 20]) == 2

    def test_mixed_ends_with_loss(self):
        """Mixed P&L ending with losses"""
        assert _calculate_streak([10, 20, -10, -20]) == -2

    def test_breakeven_last_trade(self):
        """Breakeven last trade should produce zero streak"""
        assert _calculate_streak([10, 20, 0]) == 0

    def test_breakeven_in_middle_breaks_streak(self):
        """Breakeven trade in the middle breaks the streak"""
        assert _calculate_streak([10, 0, 20, 30]) == 2

    def test_all_breakeven(self):
        """All breakeven trades produce zero streak"""
        assert _calculate_streak([0, 0, 0]) == 0

    def test_empty_pnls(self):
        """Empty P&L list produces zero streak"""
        assert _calculate_streak([]) == 0

    def test_single_win(self):
        """Single winning trade"""
        assert _calculate_streak([10]) == 1

    def test_single_loss(self):
        """Single losing trade"""
        assert _calculate_streak([-10]) == -1

    def test_single_breakeven(self):
        """Single breakeven trade"""
        assert _calculate_streak([0]) == 0
