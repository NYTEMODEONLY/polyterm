"""
AI-Powered Predictions Module

Features:
- Multi-factor signal generation
- Volume pattern recognition
- Whale behavior signals
- Confidence scoring with historical accuracy
"""

import json
import math
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

from ..db.database import Database
from ..db.models import Trade, MarketSnapshot, Wallet


class SignalType(Enum):
    """Types of prediction signals"""
    MOMENTUM = 'momentum'
    VOLUME = 'volume'
    WHALE = 'whale'
    SMART_MONEY = 'smart_money'
    ORDERBOOK = 'orderbook'
    SENTIMENT = 'sentiment'
    TECHNICAL = 'technical'


class Direction(Enum):
    """Prediction direction"""
    BULLISH = 'bullish'  # Expect price increase
    BEARISH = 'bearish'  # Expect price decrease
    NEUTRAL = 'neutral'  # No clear signal


@dataclass
class Signal:
    """Individual prediction signal"""
    signal_type: SignalType
    direction: Direction
    strength: float  # 0 to 1
    confidence: float  # 0 to 1
    value: float  # Raw signal value
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': self.signal_type.value,
            'direction': self.direction.value,
            'strength': self.strength,
            'confidence': self.confidence,
            'value': self.value,
            'description': self.description,
        }


@dataclass
class Prediction:
    """Market prediction with supporting signals"""
    market_id: str
    market_title: str
    direction: Direction
    probability_change: float  # Expected change in probability
    confidence: float  # Overall confidence 0-1
    horizon_hours: int
    signals: List[Signal] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @property
    def signal_summary(self) -> Dict[str, int]:
        """Count of signals by direction"""
        summary = {'bullish': 0, 'bearish': 0, 'neutral': 0}
        for signal in self.signals:
            summary[signal.direction.value] += 1
        return summary

    def to_dict(self) -> Dict[str, Any]:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'direction': self.direction.value,
            'probability_change': self.probability_change,
            'confidence': self.confidence,
            'horizon_hours': self.horizon_hours,
            'signal_count': len(self.signals),
            'signal_summary': self.signal_summary,
            'signals': [s.to_dict() for s in self.signals],
            'created_at': self.created_at.isoformat(),
        }


class PredictionEngine:
    """
    Multi-factor prediction engine for prediction markets.

    Combines multiple signals:
    1. Price momentum
    2. Volume acceleration
    3. Whale position changes
    4. Smart money tracking
    5. Order book imbalance
    6. Time to resolution
    """

    def __init__(self, database: Database):
        self.db = database

        # Signal weights (can be tuned)
        self.weights = {
            SignalType.MOMENTUM: 0.25,
            SignalType.VOLUME: 0.15,
            SignalType.WHALE: 0.20,
            SignalType.SMART_MONEY: 0.25,
            SignalType.ORDERBOOK: 0.10,
            SignalType.TECHNICAL: 0.05,
        }

        # Historical accuracy tracking
        self.accuracy_history: List[Dict[str, Any]] = []

    def generate_prediction(
        self,
        market_id: str,
        market_title: str = "",
        horizon_hours: int = 24,
        market_data: Optional[Dict[str, Any]] = None,
    ) -> Prediction:
        """
        Generate prediction for a market.

        Args:
            market_id: Market ID
            market_title: Market title for display
            horizon_hours: Prediction horizon
            market_data: Optional API market data with price/volume info

        Returns:
            Prediction with signals
        """
        signals = []

        # Generate individual signals - try API data first, then fall back to DB
        momentum_signal = self._calculate_momentum_signal_from_api(market_data) if market_data else None
        if not momentum_signal:
            momentum_signal = self._calculate_momentum_signal(market_id)
        if momentum_signal:
            signals.append(momentum_signal)

        volume_signal = self._calculate_volume_signal_from_api(market_data) if market_data else None
        if not volume_signal:
            volume_signal = self._calculate_volume_signal(market_id)
        if volume_signal:
            signals.append(volume_signal)

        whale_signal = self._calculate_whale_signal(market_id)
        if whale_signal:
            signals.append(whale_signal)

        smart_money_signal = self._calculate_smart_money_signal(market_id)
        if smart_money_signal:
            signals.append(smart_money_signal)

        technical_signal = self._calculate_technical_signal_from_api(market_data) if market_data else None
        if not technical_signal:
            technical_signal = self._calculate_technical_signal(market_id)
        if technical_signal:
            signals.append(technical_signal)

        # Combine signals
        direction, prob_change, confidence = self._combine_signals(signals)

        return Prediction(
            market_id=market_id,
            market_title=market_title or market_id,
            direction=direction,
            probability_change=prob_change,
            confidence=confidence,
            horizon_hours=horizon_hours,
            signals=signals,
        )

    def _calculate_momentum_signal(self, market_id: str) -> Optional[Signal]:
        """Calculate price momentum signal"""
        snapshots = self.db.get_market_history(market_id, hours=48)

        if len(snapshots) < 5:
            return None

        # Sort by timestamp
        snapshots = sorted(snapshots, key=lambda s: s.timestamp)

        # Calculate short-term and long-term price changes
        prices = [s.probability for s in snapshots]

        # Short-term: last 6 hours
        recent_count = min(6, len(prices) // 4)
        short_term_change = (prices[-1] - prices[-recent_count]) if recent_count > 0 else 0

        # Long-term: full period
        long_term_change = prices[-1] - prices[0]

        # Calculate momentum
        momentum = short_term_change * 0.7 + long_term_change * 0.3

        # Determine direction and strength
        if momentum > 0.02:
            direction = Direction.BULLISH
            strength = min(1.0, momentum * 10)
        elif momentum < -0.02:
            direction = Direction.BEARISH
            strength = min(1.0, abs(momentum) * 10)
        else:
            direction = Direction.NEUTRAL
            strength = 0.3

        return Signal(
            signal_type=SignalType.MOMENTUM,
            direction=direction,
            strength=strength,
            confidence=min(1.0, len(snapshots) / 20),  # More data = more confidence
            value=momentum,
            description=f"Price momentum: {momentum:+.1%}",
        )

    def _calculate_volume_signal(self, market_id: str) -> Optional[Signal]:
        """Calculate volume acceleration signal"""
        trades = self.db.get_trades_by_market(market_id, limit=500)

        if len(trades) < 10:
            return None

        # Sort by timestamp
        trades = sorted(trades, key=lambda t: t.timestamp)

        # Split into recent vs historical
        midpoint = len(trades) // 2
        recent_trades = trades[midpoint:]
        old_trades = trades[:midpoint]

        recent_volume = sum(t.notional for t in recent_trades)
        old_volume = sum(t.notional for t in old_trades)

        # Volume acceleration
        if old_volume > 0:
            acceleration = (recent_volume - old_volume) / old_volume
        else:
            acceleration = 0

        # High volume often precedes price movements
        # Combine with recent trade direction
        recent_buy_volume = sum(t.notional for t in recent_trades if t.side == 'BUY')
        recent_sell_volume = sum(t.notional for t in recent_trades if t.side == 'SELL')

        if recent_buy_volume > recent_sell_volume * 1.3:
            direction = Direction.BULLISH
        elif recent_sell_volume > recent_buy_volume * 1.3:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL

        strength = min(1.0, abs(acceleration))
        confidence = 0.6 if acceleration > 0.5 else 0.4

        return Signal(
            signal_type=SignalType.VOLUME,
            direction=direction,
            strength=strength,
            confidence=confidence,
            value=acceleration,
            description=f"Volume {'accelerating' if acceleration > 0 else 'decelerating'}: {acceleration:+.0%}",
        )

    def _calculate_whale_signal(self, market_id: str) -> Optional[Signal]:
        """Calculate whale activity signal"""
        # Get large trades
        large_trades = self.db.get_large_trades(min_notional=10000, hours=24)
        market_trades = [t for t in large_trades if t.market_id == market_id]

        if not market_trades:
            return None

        # Analyze whale direction
        buy_volume = sum(t.notional for t in market_trades if t.side == 'BUY' or t.outcome == 'YES')
        sell_volume = sum(t.notional for t in market_trades if t.side == 'SELL' or t.outcome == 'NO')
        total_volume = buy_volume + sell_volume

        if total_volume == 0:
            return None

        net_flow = (buy_volume - sell_volume) / total_volume

        if net_flow > 0.2:
            direction = Direction.BULLISH
        elif net_flow < -0.2:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL

        strength = min(1.0, abs(net_flow))
        confidence = min(1.0, total_volume / 100000)  # More volume = more confidence

        return Signal(
            signal_type=SignalType.WHALE,
            direction=direction,
            strength=strength,
            confidence=confidence,
            value=net_flow,
            description=f"Whale net flow: {net_flow:+.0%} (${total_volume:,.0f} total)",
        )

    def _calculate_smart_money_signal(self, market_id: str) -> Optional[Signal]:
        """Calculate smart money (high win-rate wallets) signal"""
        # Get smart money wallets
        smart_wallets = self.db.get_smart_money_wallets(min_win_rate=0.70, min_trades=10)

        if not smart_wallets:
            return None

        smart_addresses = {w.address for w in smart_wallets}

        # Get recent trades by smart money in this market
        trades = self.db.get_trades_by_market(market_id, limit=200)
        smart_trades = [t for t in trades if t.wallet_address in smart_addresses]

        if not smart_trades:
            return None

        # Analyze smart money direction
        buy_volume = sum(t.notional for t in smart_trades if t.side == 'BUY' or t.outcome == 'YES')
        sell_volume = sum(t.notional for t in smart_trades if t.side == 'SELL' or t.outcome == 'NO')
        total = buy_volume + sell_volume

        if total == 0:
            return None

        net_flow = (buy_volume - sell_volume) / total

        if net_flow > 0.3:
            direction = Direction.BULLISH
        elif net_flow < -0.3:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL

        # Higher confidence for smart money signal
        smart_trade_wallets = {t.wallet_address for t in smart_trades}
        matching_wallets = [w for w in smart_wallets if w.address in smart_trade_wallets]
        avg_win_rate = sum(w.win_rate for w in matching_wallets) / max(1, len(matching_wallets))

        return Signal(
            signal_type=SignalType.SMART_MONEY,
            direction=direction,
            strength=min(1.0, abs(net_flow) * 1.5),
            confidence=min(1.0, avg_win_rate),
            value=net_flow,
            description=f"Smart money ({len(smart_trades)} trades): {net_flow:+.0%} bias",
        )

    def _calculate_technical_signal(self, market_id: str) -> Optional[Signal]:
        """Calculate technical analysis signal (RSI-like)"""
        snapshots = self.db.get_market_history(market_id, hours=72)

        if len(snapshots) < 14:
            return None

        # Sort by timestamp
        snapshots = sorted(snapshots, key=lambda s: s.timestamp)
        prices = [s.probability for s in snapshots]

        # Calculate gains and losses
        gains = []
        losses = []

        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change > 0:
                gains.append(change)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(change))

        # RSI calculation (14-period)
        period = min(14, len(gains))
        avg_gain = sum(gains[-period:]) / period if gains else 0
        avg_loss = sum(losses[-period:]) / period if losses else 0.001

        rs = avg_gain / avg_loss if avg_loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))

        # Interpret RSI
        if rsi > 70:
            direction = Direction.BEARISH  # Overbought
            strength = min(1.0, (rsi - 70) / 30)
            description = f"RSI {rsi:.0f} (overbought)"
        elif rsi < 30:
            direction = Direction.BULLISH  # Oversold
            strength = min(1.0, (30 - rsi) / 30)
            description = f"RSI {rsi:.0f} (oversold)"
        else:
            direction = Direction.NEUTRAL
            strength = 0.3
            description = f"RSI {rsi:.0f} (neutral)"

        return Signal(
            signal_type=SignalType.TECHNICAL,
            direction=direction,
            strength=strength,
            confidence=0.5,  # Technical analysis has moderate confidence
            value=rsi,
            description=description,
        )

    def _calculate_momentum_signal_from_api(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """Calculate momentum signal from API price change data"""
        if not market_data:
            return None

        # Extract price changes from API data
        one_day_change = market_data.get('oneDayPriceChange')
        one_week_change = market_data.get('oneWeekPriceChange')
        one_month_change = market_data.get('oneMonthPriceChange')

        # Need at least one price change metric
        if one_day_change is None and one_week_change is None:
            return None

        # Convert to float if string
        try:
            if one_day_change is not None:
                one_day_change = float(one_day_change)
            if one_week_change is not None:
                one_week_change = float(one_week_change)
            if one_month_change is not None:
                one_month_change = float(one_month_change)
        except (ValueError, TypeError):
            return None

        # Calculate weighted momentum (short-term weighted higher)
        momentum = 0
        weight_sum = 0

        if one_day_change is not None:
            momentum += one_day_change * 0.5
            weight_sum += 0.5
        if one_week_change is not None:
            momentum += one_week_change * 0.35
            weight_sum += 0.35
        if one_month_change is not None:
            momentum += one_month_change * 0.15
            weight_sum += 0.15

        if weight_sum > 0:
            momentum = momentum / weight_sum

        # Determine direction and strength
        if momentum > 0.02:
            direction = Direction.BULLISH
            strength = min(1.0, momentum * 5)
        elif momentum < -0.02:
            direction = Direction.BEARISH
            strength = min(1.0, abs(momentum) * 5)
        else:
            direction = Direction.NEUTRAL
            strength = 0.3

        # Higher confidence when we have more data points
        data_points = sum(1 for x in [one_day_change, one_week_change, one_month_change] if x is not None)
        confidence = min(1.0, 0.4 + (data_points * 0.2))

        return Signal(
            signal_type=SignalType.MOMENTUM,
            direction=direction,
            strength=strength,
            confidence=confidence,
            value=momentum,
            description=f"Price momentum: {momentum:+.1%} (1d: {one_day_change:+.1%})" if one_day_change else f"Price momentum: {momentum:+.1%}",
        )

    def _calculate_volume_signal_from_api(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """Calculate volume signal from API volume data"""
        if not market_data:
            return None

        # Extract volume data
        volume_24hr = market_data.get('volume24hr')
        total_volume = market_data.get('volume')
        liquidity = market_data.get('liquidity')

        # Try alternative field names
        if volume_24hr is None:
            volume_24hr = market_data.get('volume24Hour')
        if total_volume is None:
            total_volume = market_data.get('volumeNum')

        # Need at least 24hr volume
        if volume_24hr is None:
            return None

        try:
            volume_24hr = float(volume_24hr)
            total_volume = float(total_volume) if total_volume else 0
            liquidity = float(liquidity) if liquidity else 0
        except (ValueError, TypeError):
            return None

        # Calculate volume acceleration if we have total volume
        if total_volume > 0:
            # Estimate 7-day average daily volume (rough approximation)
            avg_daily_volume = total_volume / 30  # Assume market existed ~30 days
            acceleration = (volume_24hr - avg_daily_volume) / avg_daily_volume if avg_daily_volume > 0 else 0
        else:
            acceleration = 0

        # Volume level analysis
        if volume_24hr > 100000:
            volume_level = "very high"
            base_strength = 0.8
        elif volume_24hr > 50000:
            volume_level = "high"
            base_strength = 0.6
        elif volume_24hr > 10000:
            volume_level = "moderate"
            base_strength = 0.4
        else:
            volume_level = "low"
            base_strength = 0.2

        # Direction based on price movement (combine with momentum if available)
        one_day_change = market_data.get('oneDayPriceChange')
        if one_day_change is not None:
            try:
                one_day_change = float(one_day_change)
                if one_day_change > 0.02 and volume_24hr > 10000:
                    direction = Direction.BULLISH
                elif one_day_change < -0.02 and volume_24hr > 10000:
                    direction = Direction.BEARISH
                else:
                    direction = Direction.NEUTRAL
            except (ValueError, TypeError):
                direction = Direction.NEUTRAL
        else:
            direction = Direction.NEUTRAL

        strength = min(1.0, base_strength + abs(acceleration) * 0.2)
        confidence = 0.5 if volume_24hr > 10000 else 0.3

        return Signal(
            signal_type=SignalType.VOLUME,
            direction=direction,
            strength=strength,
            confidence=confidence,
            value=acceleration,
            description=f"Volume {volume_level}: ${volume_24hr:,.0f}/24h",
        )

    def _calculate_technical_signal_from_api(self, market_data: Dict[str, Any]) -> Optional[Signal]:
        """Calculate technical signal from API price data"""
        if not market_data:
            return None

        # Get current price
        outcome_prices = market_data.get('outcomePrices')
        if not outcome_prices:
            return None

        try:
            if isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                current_price = float(outcome_prices[0])
            elif isinstance(outcome_prices, str):
                # Parse JSON string if needed
                prices = json.loads(outcome_prices)
                current_price = float(prices[0]) if prices else None
            else:
                return None
        except (ValueError, TypeError, json.JSONDecodeError):
            return None

        if current_price is None:
            return None

        # Simple overbought/oversold based on extreme probabilities
        if current_price > 0.85:
            direction = Direction.BEARISH
            strength = min(1.0, (current_price - 0.85) * 5)
            description = f"High probability {current_price:.0%} (potential overconfidence)"
        elif current_price < 0.15:
            direction = Direction.BULLISH
            strength = min(1.0, (0.15 - current_price) * 5)
            description = f"Low probability {current_price:.0%} (potential underconfidence)"
        else:
            direction = Direction.NEUTRAL
            strength = 0.2
            description = f"Price {current_price:.0%} (neutral range)"

        return Signal(
            signal_type=SignalType.TECHNICAL,
            direction=direction,
            strength=strength,
            confidence=0.4,  # Lower confidence for simple technical analysis
            value=current_price,
            description=description,
        )

    def _combine_signals(
        self,
        signals: List[Signal],
    ) -> Tuple[Direction, float, float]:
        """
        Combine multiple signals into overall prediction.

        Returns:
            (direction, probability_change, confidence)
        """
        if not signals:
            return Direction.NEUTRAL, 0.0, 0.0

        # Calculate weighted score
        total_weight = 0
        weighted_score = 0
        weighted_confidence = 0

        for signal in signals:
            weight = self.weights.get(signal.signal_type, 0.1)

            # Convert direction to numeric
            direction_score = {
                Direction.BULLISH: 1.0,
                Direction.BEARISH: -1.0,
                Direction.NEUTRAL: 0.0,
            }.get(signal.direction, 0)

            signal_score = direction_score * signal.strength
            weighted_score += signal_score * weight * signal.confidence
            weighted_confidence += signal.confidence * weight
            total_weight += weight

        if total_weight == 0:
            return Direction.NEUTRAL, 0.0, 0.0

        avg_score = weighted_score / total_weight
        avg_confidence = weighted_confidence / total_weight

        # Determine direction
        if avg_score > 0.2:
            direction = Direction.BULLISH
        elif avg_score < -0.2:
            direction = Direction.BEARISH
        else:
            direction = Direction.NEUTRAL

        # Estimate probability change (scaled to percentage points)
        prob_change = avg_score * 10  # -10% to +10%

        return direction, prob_change, avg_confidence

    def record_outcome(
        self,
        prediction: Prediction,
        actual_change: float,
    ) -> None:
        """
        Record prediction outcome for accuracy tracking.

        Args:
            prediction: Original prediction
            actual_change: Actual probability change
        """
        correct = (
            (prediction.probability_change > 0 and actual_change > 0) or
            (prediction.probability_change < 0 and actual_change < 0) or
            (abs(prediction.probability_change) < 1 and abs(actual_change) < 1)
        )

        self.accuracy_history.append({
            'timestamp': datetime.now(),
            'market_id': prediction.market_id,
            'predicted_direction': prediction.direction.value,
            'predicted_change': prediction.probability_change,
            'actual_change': actual_change,
            'confidence': prediction.confidence,
            'correct': correct,
        })

        # Keep last 1000 predictions
        if len(self.accuracy_history) > 1000:
            self.accuracy_history = self.accuracy_history[-1000:]

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get historical accuracy statistics"""
        if not self.accuracy_history:
            return {'total_predictions': 0, 'accuracy': 0.0}

        correct = sum(1 for p in self.accuracy_history if p['correct'])
        total = len(self.accuracy_history)

        # Confidence-weighted accuracy
        weighted_correct = sum(
            p['confidence'] for p in self.accuracy_history if p['correct']
        )
        total_confidence = sum(p['confidence'] for p in self.accuracy_history)
        weighted_accuracy = weighted_correct / total_confidence if total_confidence > 0 else 0

        return {
            'total_predictions': total,
            'correct_predictions': correct,
            'accuracy': correct / total,
            'weighted_accuracy': weighted_accuracy,
            'recent_accuracy': self._get_recent_accuracy(24),
        }

    def _get_recent_accuracy(self, hours: int) -> float:
        """Get accuracy for recent predictions"""
        cutoff = datetime.now() - timedelta(hours=hours)
        recent = [p for p in self.accuracy_history if p['timestamp'] > cutoff]

        if not recent:
            return 0.0

        correct = sum(1 for p in recent if p['correct'])
        return correct / len(recent)

    def format_prediction(self, prediction: Prediction) -> str:
        """Format prediction for display"""
        lines = []

        # Header
        direction_emoji = {
            Direction.BULLISH: '+',
            Direction.BEARISH: '-',
            Direction.NEUTRAL: '~',
        }.get(prediction.direction, '?')

        lines.append(f"=== Prediction: {prediction.market_title[:40]} ===")
        lines.append(f"Direction: {direction_emoji} {prediction.direction.value.upper()}")
        lines.append(f"Expected Change: {prediction.probability_change:+.1f}%")
        lines.append(f"Confidence: {prediction.confidence:.0%}")
        lines.append(f"Horizon: {prediction.horizon_hours} hours")
        lines.append("")

        # Signals
        lines.append(f"Signals ({len(prediction.signals)}):")
        for signal in prediction.signals:
            dir_symbol = '+' if signal.direction == Direction.BULLISH else '-' if signal.direction == Direction.BEARISH else '~'
            lines.append(f"  [{dir_symbol}] {signal.signal_type.value}: {signal.description}")
            lines.append(f"      Strength: {signal.strength:.0%}, Confidence: {signal.confidence:.0%}")

        # Summary
        lines.append("")
        summary = prediction.signal_summary
        lines.append(f"Signal Summary: {summary['bullish']} bullish, {summary['bearish']} bearish, {summary['neutral']} neutral")

        return "\n".join(lines)
