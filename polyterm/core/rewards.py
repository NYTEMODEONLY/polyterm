"""Rewards Calculator for Polymarket

Estimates holding rewards (4% APY on qualifying positions) and
liquidity provision reward eligibility.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta


class RewardsCalculator:
    """Calculate estimated Polymarket rewards"""

    HOLDING_APY = 0.04  # 4% APY on qualifying positions
    DAILY_RATE = HOLDING_APY / 365
    QUALIFYING_MIN = 0.20  # Position must be >= 20 cents
    QUALIFYING_MAX = 0.80  # Position must be <= 80 cents
    MIN_HOLD_HOURS = 24  # Must hold for at least 24 hours

    def is_position_qualifying(self, price, hold_hours=None):
        """Check if a position qualifies for holding rewards

        Qualifying criteria:
        - Position price must be between 20-80 cents (near midpoint)
        - Position must be held for at least 24 hours
        """
        if price < self.QUALIFYING_MIN or price > self.QUALIFYING_MAX:
            return False
        if hold_hours is not None and hold_hours < self.MIN_HOLD_HOURS:
            return False
        return True

    def estimate_holding_rewards(self, positions):
        """Estimate daily/weekly/monthly holding rewards for a list of positions

        Args:
            positions: List of dicts with keys: 'value' (dollar value),
                      'price' (entry price 0-1), 'hold_hours' (hours held)

        Returns:
            Dict with reward estimates and per-position breakdown
        """
        qualifying = []
        non_qualifying = []
        total_qualifying_value = 0.0

        for pos in positions:
            value = float(pos.get('value', 0))
            price = float(pos.get('price', 0.5))
            hold_hours = pos.get('hold_hours')

            if self.is_position_qualifying(price, hold_hours):
                qualifying.append(pos)
                total_qualifying_value += value
            else:
                non_qualifying.append(pos)

        daily = total_qualifying_value * self.DAILY_RATE
        weekly = daily * 7
        monthly = daily * 30
        yearly = total_qualifying_value * self.HOLDING_APY

        return {
            'qualifying_positions': len(qualifying),
            'non_qualifying_positions': len(non_qualifying),
            'total_qualifying_value': round(total_qualifying_value, 2),
            'estimated_daily': round(daily, 4),
            'estimated_weekly': round(weekly, 4),
            'estimated_monthly': round(monthly, 2),
            'estimated_yearly': round(yearly, 2),
            'apy': self.HOLDING_APY,
        }

    def estimate_liquidity_rewards(self, open_orders):
        """Estimate liquidity provision reward eligibility

        Args:
            open_orders: List of dicts with 'price', 'size', 'side', 'market_midpoint'

        Returns:
            Dict with liquidity reward eligibility info
        """
        if not open_orders:
            return {
                'eligible_orders': 0,
                'total_order_value': 0,
                'avg_distance_from_mid': 0,
                'eligible': False,
                'note': 'No open orders found',
            }

        eligible = []
        total_value = 0.0
        distances = []

        for order in open_orders:
            price = float(order.get('price', 0))
            size = float(order.get('size', 0))
            midpoint = float(order.get('market_midpoint', 0.5))

            distance = abs(price - midpoint)
            value = price * size
            total_value += value

            # Orders within 5 cents of midpoint are more likely to earn rewards
            if distance <= 0.05 and value >= 10:
                eligible.append(order)
                distances.append(distance)

        avg_distance = sum(distances) / len(distances) if distances else 0

        return {
            'eligible_orders': len(eligible),
            'total_order_value': round(total_value, 2),
            'avg_distance_from_mid': round(avg_distance, 4),
            'eligible': len(eligible) > 0,
            'note': 'Closer to midpoint = higher rewards' if eligible else 'Place orders closer to market midpoint',
        }

    def calculate_effective_yield(self, position_value, holding_days):
        """Calculate effective yield including holding rewards

        Args:
            position_value: Dollar value of position
            holding_days: Number of days held

        Returns:
            Dict with yield calculations
        """
        if position_value <= 0 or holding_days <= 0:
            return {
                'total_reward': 0,
                'effective_apy': 0,
                'daily_reward': 0,
            }

        total_reward = position_value * self.DAILY_RATE * holding_days
        effective_apy = (total_reward / position_value) * (365 / holding_days) if holding_days > 0 else 0

        return {
            'total_reward': round(total_reward, 4),
            'effective_apy': round(effective_apy, 4),
            'daily_reward': round(position_value * self.DAILY_RATE, 4),
            'holding_days': holding_days,
            'position_value': position_value,
        }
