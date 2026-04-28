"""Tests for CLOB V2 fee calculations."""

import pytest

from polyterm.core.fees import (
    FeeSchedule,
    breakeven_price,
    effective_taker_fee_rate,
    estimate_taker_fee,
    fee_schedule_from_clob_fee_rate,
    fee_schedule_from_market,
)


class TestFeeScheduleParsing:
    """Test fee schedule extraction from API payloads."""

    def test_extracts_gamma_fee_schedule(self):
        market = {
            "feesEnabled": True,
            "feeSchedule": {
                "rate": 0.05,
                "exponent": 1,
                "takerOnly": True,
            },
        }

        schedule = fee_schedule_from_market(market)

        assert schedule.rate == 0.05
        assert schedule.exponent == 1
        assert schedule.taker_only is True
        assert schedule.source == "market"

    def test_disabled_market_fees_returns_zero_schedule(self):
        schedule = fee_schedule_from_market({"feesEnabled": False})

        assert schedule.rate == 0
        assert estimate_taker_fee(100, 0.5, schedule) == 0

    def test_extracts_clob_fee_rate(self):
        schedule = fee_schedule_from_clob_fee_rate({"base_fee": 1000})

        assert schedule.rate == pytest.approx(0.10)
        assert schedule.source == "clob"


class TestDynamicFeeCurve:
    """Test CLOB V2 price-sensitive fee math."""

    def test_fee_peaks_near_midpoint(self):
        schedule = FeeSchedule(rate=0.05)

        low = effective_taker_fee_rate(0.10, schedule)
        mid = effective_taker_fee_rate(0.50, schedule)
        high = effective_taker_fee_rate(0.90, schedule)

        assert mid > low
        assert mid > high
        assert low == pytest.approx(high)

    def test_estimated_fee_uses_trade_notional(self):
        schedule = FeeSchedule(rate=0.05)

        fee = estimate_taker_fee(100, 0.50, schedule)

        assert fee == pytest.approx(1.25)

    def test_breakeven_accounts_for_dynamic_fee(self):
        schedule = FeeSchedule(rate=0.05)

        breakeven = breakeven_price(0.50, schedule)

        assert breakeven == pytest.approx(0.50625)
        assert breakeven < 1.0

    def test_breakeven_never_exceeds_one(self):
        schedule = FeeSchedule(rate=0.20)

        assert breakeven_price(0.99, schedule) <= 1.0
