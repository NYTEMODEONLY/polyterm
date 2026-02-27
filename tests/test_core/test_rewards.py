"""Tests for RewardsCalculator"""

import pytest
from polyterm.core.rewards import RewardsCalculator


class TestRewardsQualification:
    """Test position qualification logic"""

    def test_price_mid_range_qualifies(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.5) is True

    def test_price_too_low_does_not_qualify(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.1) is False

    def test_price_too_high_does_not_qualify(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.9) is False

    def test_boundary_min_qualifies(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.20) is True

    def test_boundary_max_qualifies(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.80) is True

    def test_just_below_min_does_not_qualify(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.19) is False

    def test_just_above_max_does_not_qualify(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.81) is False

    def test_hold_hours_less_than_24_does_not_qualify(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.5, hold_hours=23) is False

    def test_hold_hours_exactly_24_qualifies(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.5, hold_hours=24) is True

    def test_hold_hours_more_than_24_qualifies(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.5, hold_hours=48) is True

    def test_hold_hours_none_qualifies_no_check(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.5, hold_hours=None) is True

    def test_price_qualifying_but_hold_too_short(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.5, hold_hours=12) is False

    def test_price_not_qualifying_even_with_long_hold(self):
        calc = RewardsCalculator()
        assert calc.is_position_qualifying(0.1, hold_hours=100) is False


class TestEstimateHoldingRewards:
    """Test holding reward estimation"""

    def test_single_qualifying_position(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.5, 'hold_hours': 48}
        ]
        result = calc.estimate_holding_rewards(positions)

        assert result['qualifying_positions'] == 1
        assert result['non_qualifying_positions'] == 0
        assert result['total_qualifying_value'] == 1000
        assert result['apy'] == 0.04

        # Check daily reward: 1000 * 0.04 / 365 ≈ 0.1096
        assert 0.109 < result['estimated_daily'] < 0.110

        # Check yearly: 1000 * 0.04 = 40
        assert result['estimated_yearly'] == 40

    def test_mixed_qualifying_and_non_qualifying(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.5, 'hold_hours': 48},  # qualifies
            {'value': 500, 'price': 0.1, 'hold_hours': 48},   # price too low
            {'value': 300, 'price': 0.6, 'hold_hours': 12},   # hold too short
        ]
        result = calc.estimate_holding_rewards(positions)

        assert result['qualifying_positions'] == 1
        assert result['non_qualifying_positions'] == 2
        assert result['total_qualifying_value'] == 1000

    def test_all_qualifying(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.5, 'hold_hours': 48},
            {'value': 500, 'price': 0.4, 'hold_hours': 72},
            {'value': 300, 'price': 0.6, 'hold_hours': 24},
        ]
        result = calc.estimate_holding_rewards(positions)

        assert result['qualifying_positions'] == 3
        assert result['non_qualifying_positions'] == 0
        assert result['total_qualifying_value'] == 1800

    def test_none_qualifying(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.1, 'hold_hours': 48},
            {'value': 500, 'price': 0.9, 'hold_hours': 48},
        ]
        result = calc.estimate_holding_rewards(positions)

        assert result['qualifying_positions'] == 0
        assert result['non_qualifying_positions'] == 2
        assert result['total_qualifying_value'] == 0
        assert result['estimated_daily'] == 0
        assert result['estimated_yearly'] == 0

    def test_empty_positions(self):
        calc = RewardsCalculator()
        result = calc.estimate_holding_rewards([])

        assert result['qualifying_positions'] == 0
        assert result['non_qualifying_positions'] == 0
        assert result['total_qualifying_value'] == 0
        assert result['estimated_daily'] == 0

    def test_large_value_position(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 100000, 'price': 0.5, 'hold_hours': 48}
        ]
        result = calc.estimate_holding_rewards(positions)

        assert result['qualifying_positions'] == 1
        assert result['total_qualifying_value'] == 100000
        assert result['estimated_yearly'] == 4000  # 100k * 0.04

    def test_zero_value_position(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 0, 'price': 0.5, 'hold_hours': 48}
        ]
        result = calc.estimate_holding_rewards(positions)

        assert result['qualifying_positions'] == 1
        assert result['total_qualifying_value'] == 0
        assert result['estimated_daily'] == 0

    def test_weekly_calculation(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.5, 'hold_hours': 48}
        ]
        result = calc.estimate_holding_rewards(positions)

        # Weekly should be daily * 7
        expected_weekly = result['estimated_daily'] * 7
        assert abs(result['estimated_weekly'] - expected_weekly) < 0.0001

    def test_monthly_calculation(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.5, 'hold_hours': 48}
        ]
        result = calc.estimate_holding_rewards(positions)

        # Monthly should be daily * 30
        expected_monthly = result['estimated_daily'] * 30
        assert abs(result['estimated_monthly'] - expected_monthly) < 0.01

    def test_position_without_hold_hours(self):
        calc = RewardsCalculator()
        positions = [
            {'value': 1000, 'price': 0.5}  # No hold_hours key
        ]
        result = calc.estimate_holding_rewards(positions)

        # Should still qualify (no hold time check)
        assert result['qualifying_positions'] == 1
        assert result['total_qualifying_value'] == 1000


class TestEstimateLiquidityRewards:
    """Test liquidity reward estimation"""

    def test_eligible_orders_close_to_midpoint(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.50, 'size': 100, 'market_midpoint': 0.51},  # 0.01 distance, $50 value
            {'price': 0.52, 'size': 50, 'market_midpoint': 0.51},   # 0.01 distance, $26 value
        ]
        result = calc.estimate_liquidity_rewards(orders)

        assert result['eligible_orders'] == 2
        assert result['eligible'] is True
        assert result['avg_distance_from_mid'] < 0.02
        assert 'higher rewards' in result['note']

    def test_no_eligible_orders_far_from_midpoint(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.30, 'size': 100, 'market_midpoint': 0.51},  # 0.21 distance
            {'price': 0.72, 'size': 50, 'market_midpoint': 0.51},   # 0.21 distance
        ]
        result = calc.estimate_liquidity_rewards(orders)

        assert result['eligible_orders'] == 0
        assert result['eligible'] is False
        assert 'closer to market midpoint' in result['note']

    def test_empty_orders(self):
        calc = RewardsCalculator()
        result = calc.estimate_liquidity_rewards([])

        assert result['eligible_orders'] == 0
        assert result['total_order_value'] == 0
        assert result['avg_distance_from_mid'] == 0
        assert result['eligible'] is False
        assert 'No open orders found' in result['note']

    def test_orders_close_but_small_value(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.50, 'size': 10, 'market_midpoint': 0.51},  # 0.01 distance but only $5 value
        ]
        result = calc.estimate_liquidity_rewards(orders)

        # Should not be eligible due to value < $10
        assert result['eligible_orders'] == 0
        assert result['eligible'] is False

    def test_orders_at_boundary_distance(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.55, 'size': 100, 'market_midpoint': 0.51},  # 0.04 distance (safely within boundary), $55 value
        ]
        result = calc.estimate_liquidity_rewards(orders)

        assert result['eligible_orders'] == 1
        assert result['eligible'] is True

    def test_orders_just_over_boundary_distance(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.57, 'size': 100, 'market_midpoint': 0.51},  # 0.06 distance
        ]
        result = calc.estimate_liquidity_rewards(orders)

        assert result['eligible_orders'] == 0
        assert result['eligible'] is False

    def test_total_order_value_calculation(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.50, 'size': 100, 'market_midpoint': 0.51},  # $50
            {'price': 0.30, 'size': 100, 'market_midpoint': 0.51},  # $30 (not eligible)
        ]
        result = calc.estimate_liquidity_rewards(orders)

        # Total value should include all orders, not just eligible
        assert result['total_order_value'] == 80

    def test_avg_distance_calculation(self):
        calc = RewardsCalculator()
        orders = [
            {'price': 0.50, 'size': 100, 'market_midpoint': 0.51},  # 0.01 distance, $50 value
            {'price': 0.54, 'size': 100, 'market_midpoint': 0.51},  # 0.03 distance, $54 value
        ]
        result = calc.estimate_liquidity_rewards(orders)

        # Both eligible (within 0.05 and > $10)
        # Avg distance = (0.01 + 0.03) / 2 = 0.02
        assert result['avg_distance_from_mid'] == 0.02


class TestEffectiveYield:
    """Test effective yield calculations"""

    def test_basic_calculation(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 30)

        # 30 days at 4% APY
        expected_daily = 1000 * calc.DAILY_RATE
        expected_total = expected_daily * 30

        assert abs(result['total_reward'] - expected_total) < 0.001
        assert result['holding_days'] == 30
        assert result['position_value'] == 1000

    def test_zero_value_returns_zero(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(0, 30)

        assert result['total_reward'] == 0
        assert result['effective_apy'] == 0
        assert result['daily_reward'] == 0

    def test_zero_days_returns_zero(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 0)

        assert result['total_reward'] == 0
        assert result['effective_apy'] == 0
        assert result['daily_reward'] == 0

    def test_negative_value_returns_zero(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(-1000, 30)

        assert result['total_reward'] == 0
        assert result['effective_apy'] == 0

    def test_negative_days_returns_zero(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, -30)

        assert result['total_reward'] == 0
        assert result['effective_apy'] == 0

    def test_365_days_equals_apy(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 365)

        # After 365 days, effective APY should equal stated APY (4%)
        assert abs(result['effective_apy'] - 0.04) < 0.0001

    def test_one_day_holding(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 1)

        expected_daily = 1000 * calc.DAILY_RATE
        assert abs(result['total_reward'] - expected_daily) < 0.001
        assert abs(result['daily_reward'] - expected_daily) < 0.001

        # Effective APY for 1 day extrapolated to year should equal stated APY
        assert abs(result['effective_apy'] - 0.04) < 0.0001

    def test_30_day_holding(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 30)

        # Should be close to 4% APY when annualized
        assert abs(result['effective_apy'] - 0.04) < 0.0001

    def test_large_position_value(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(100000, 365)

        # 100k at 4% for 365 days = $4000
        assert abs(result['total_reward'] - 4000) < 1

    def test_daily_reward_consistency(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 10)

        # Daily reward should be the same regardless of holding period
        expected_daily = 1000 * calc.DAILY_RATE
        assert abs(result['daily_reward'] - expected_daily) < 0.001

        # Total should be daily * days
        assert abs(result['total_reward'] - (expected_daily * 10)) < 0.001

    def test_fractional_days(self):
        calc = RewardsCalculator()
        result = calc.calculate_effective_yield(1000, 7.5)

        expected_daily = 1000 * calc.DAILY_RATE
        expected_total = expected_daily * 7.5

        assert abs(result['total_reward'] - expected_total) < 0.001
