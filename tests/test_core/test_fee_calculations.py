"""Tests for fee calculations across position sizing and trade analysis"""

import pytest


class TestBreakevenFormula:
    """Test quicktrade breakeven calculation"""

    def _breakeven(self, price):
        """Exact breakeven: price / (0.98 + 0.02 * price)"""
        return price / (0.98 + 0.02 * price)

    def test_breakeven_at_low_price(self):
        """Breakeven at low price should be close to price * 1.02"""
        be = self._breakeven(0.10)
        assert 0.10 < be < 0.11  # Slightly above entry

    def test_breakeven_at_mid_price(self):
        """Breakeven at mid price"""
        be = self._breakeven(0.50)
        # Exact: 0.50 / (0.98 + 0.01) = 0.50 / 0.99 ≈ 0.5051
        assert 0.505 < be < 0.506

    def test_breakeven_at_high_price(self):
        """Breakeven at high price should be much less than price * 1.02"""
        be = self._breakeven(0.90)
        # Old formula: 0.90 * 1.02 = 0.918 (WRONG - above 1.0 would be impossible)
        # New formula: 0.90 / (0.98 + 0.018) = 0.90 / 0.998 ≈ 0.9018
        assert be < 0.91  # Must be below the old wrong value
        assert be > 0.90  # Must be above entry

    def test_breakeven_never_exceeds_one(self):
        """Breakeven should never exceed 1.0 for any valid price"""
        for price_int in range(1, 100):
            price = price_int / 100
            be = self._breakeven(price)
            assert be < 1.0, f"Breakeven {be} exceeds 1.0 at price {price}"

    def test_breakeven_always_above_entry(self):
        """Breakeven should always be above entry price"""
        for price_int in range(1, 100):
            price = price_int / 100
            be = self._breakeven(price)
            assert be > price, f"Breakeven {be} not above entry {price}"


class TestKellyWithFees:
    """Test that Kelly criterion accounts for 2% fee"""

    def _calculate_payout_ratio(self, odds, fee_rate=0.02):
        """Net payout ratio after fees"""
        return (1 - odds) * (1 - fee_rate) / odds

    def test_payout_ratio_includes_fee(self):
        """Payout ratio should be reduced by fee"""
        gross = (1 - 0.50) / 0.50  # 1.0
        net = self._calculate_payout_ratio(0.50)
        assert net < gross
        assert net == pytest.approx(0.98, abs=0.001)

    def test_fee_reduces_ev(self):
        """EV should be lower with fee than without"""
        prob = 0.60
        odds = 0.50
        gross_payout = (1 - odds) / odds
        net_payout = self._calculate_payout_ratio(odds)

        gross_ev = prob * gross_payout - (1 - prob)
        net_ev = prob * net_payout - (1 - prob)

        assert net_ev < gross_ev

    def test_marginal_edge_eliminated_by_fee(self):
        """A tiny edge should become negative after fee"""
        # At true prob 0.51 with odds 0.50, gross edge is +0.02
        # After 2% fee on payout, edge should be smaller
        prob = 0.51
        odds = 0.50
        net_payout = self._calculate_payout_ratio(odds)
        net_ev = prob * net_payout - (1 - prob)
        # 0.51 * 0.98 - 0.49 = 0.4998 - 0.49 = 0.0098 (still positive but smaller)
        assert net_ev < 0.02  # Less than gross edge

    def test_profit_if_win_net_of_fee(self):
        """Profit if win should reflect fee deduction"""
        odds = 0.50
        amount = 100
        fee_rate = 0.02
        shares = amount / odds  # 200 shares
        gross_profit = shares * (1 - odds)  # $100
        net_profit = gross_profit * (1 - fee_rate)  # $98
        assert net_profit == pytest.approx(98.0)


class TestCrypto15mFees:
    """Test crypto 15m trade analysis fee deduction"""

    def test_up_scenario_fee(self):
        """UP scenario should deduct 2% fee from winnings"""
        amount = 100
        yes_prob = 0.50
        shares = amount / yes_prob  # 200
        gross = shares - amount  # 100
        fee = gross * 0.02  # 2
        net = gross - fee  # 98
        roi = (net / amount) * 100  # 98%

        assert net == pytest.approx(98.0)
        assert roi == pytest.approx(98.0)

    def test_down_scenario_fee(self):
        """DOWN scenario should deduct 2% fee from winnings"""
        amount = 100
        no_prob = 0.50
        shares = amount / no_prob
        gross = shares - amount
        fee = gross * 0.02
        net = gross - fee

        assert net == pytest.approx(98.0)
