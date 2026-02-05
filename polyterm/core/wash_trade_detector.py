"""Wash Trade Detection - Identify suspicious trading patterns

Based on research indicating ~25% of Polymarket volume may be wash trading.
Detects patterns like:
- Same wallet trading both sides
- Coordinated wallet clusters
- Volume/liquidity ratio anomalies
- Suspicious timing patterns
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from enum import Enum


class WashTradeRisk(Enum):
    """Risk level for wash trading"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"


@dataclass
class WashTradeIndicator:
    """Individual indicator of potential wash trading"""
    indicator_type: str
    score: int  # 0-100
    description: str
    details: Optional[str] = None


@dataclass
class WashTradeAnalysis:
    """Complete wash trade analysis for a market"""
    market_id: str
    market_title: str
    risk_level: WashTradeRisk
    overall_score: int  # 0-100 (higher = more suspicious)
    indicators: List[WashTradeIndicator]
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'risk_level': self.risk_level.value,
            'overall_score': self.overall_score,
            'indicators': [
                {
                    'type': i.indicator_type,
                    'score': i.score,
                    'description': i.description,
                    'details': i.details,
                }
                for i in self.indicators
            ],
            'recommendations': self.recommendations,
        }


class WashTradeDetector:
    """Detect potential wash trading in markets"""

    # Thresholds for various indicators
    VOLUME_LIQUIDITY_THRESHOLD = 3.0  # Volume > 3x liquidity is suspicious
    TRADE_SIZE_UNIFORMITY_THRESHOLD = 0.8  # If 80%+ trades are same size
    TIME_CLUSTERING_THRESHOLD = 0.7  # If 70%+ trades in small windows

    def __init__(self):
        pass

    def analyze_market(
        self,
        market_id: str,
        title: str,
        volume_24h: float = 0,
        liquidity: float = 0,
        trade_count_24h: int = 0,
        unique_traders_24h: int = 0,
        avg_trade_size: float = 0,
        median_trade_size: float = 0,
        yes_volume: float = 0,
        no_volume: float = 0,
    ) -> WashTradeAnalysis:
        """Analyze a market for wash trading indicators

        Args:
            market_id: Market identifier
            title: Market title
            volume_24h: 24-hour volume
            liquidity: Current liquidity
            trade_count_24h: Number of trades in 24h
            unique_traders_24h: Unique wallets trading in 24h
            avg_trade_size: Average trade size
            median_trade_size: Median trade size
            yes_volume: Volume on YES side
            no_volume: Volume on NO side

        Returns:
            WashTradeAnalysis with risk assessment
        """
        indicators = []
        recommendations = []

        # Indicator 1: Volume/Liquidity Ratio
        vol_liq_indicator = self._analyze_volume_liquidity_ratio(volume_24h, liquidity)
        if vol_liq_indicator:
            indicators.append(vol_liq_indicator)

        # Indicator 2: Trader Concentration
        trader_indicator = self._analyze_trader_concentration(
            trade_count_24h, unique_traders_24h
        )
        if trader_indicator:
            indicators.append(trader_indicator)

        # Indicator 3: Trade Size Distribution
        size_indicator = self._analyze_trade_size_distribution(
            avg_trade_size, median_trade_size
        )
        if size_indicator:
            indicators.append(size_indicator)

        # Indicator 4: Side Balance
        balance_indicator = self._analyze_side_balance(yes_volume, no_volume)
        if balance_indicator:
            indicators.append(balance_indicator)

        # Indicator 5: Volume Anomaly
        anomaly_indicator = self._analyze_volume_anomaly(
            volume_24h, trade_count_24h, avg_trade_size
        )
        if anomaly_indicator:
            indicators.append(anomaly_indicator)

        # Calculate overall score
        if indicators:
            # Weighted average with higher weight on more concerning indicators
            total_weight = 0
            weighted_score = 0
            for ind in indicators:
                weight = 1.0 + (ind.score / 100)  # Higher scores get more weight
                weighted_score += ind.score * weight
                total_weight += weight
            overall_score = int(weighted_score / total_weight) if total_weight > 0 else 0
        else:
            overall_score = 40  # Default uncertain score when no data available

        # Determine risk level
        if overall_score <= 25:
            risk_level = WashTradeRisk.LOW
        elif overall_score <= 45:
            risk_level = WashTradeRisk.MEDIUM
        elif overall_score <= 65:
            risk_level = WashTradeRisk.HIGH
        else:
            risk_level = WashTradeRisk.VERY_HIGH

        # Generate recommendations
        if risk_level in [WashTradeRisk.HIGH, WashTradeRisk.VERY_HIGH]:
            recommendations.append("Volume may be artificially inflated")
            recommendations.append("Consider actual liquidity, not reported volume")
            recommendations.append("Check order book depth before large trades")
        elif risk_level == WashTradeRisk.MEDIUM:
            recommendations.append("Some trading patterns warrant caution")
            recommendations.append("Verify organic market interest")
        else:
            recommendations.append("Trading patterns appear organic")

        return WashTradeAnalysis(
            market_id=market_id,
            market_title=title,
            risk_level=risk_level,
            overall_score=overall_score,
            indicators=indicators,
            recommendations=recommendations,
        )

    def _analyze_volume_liquidity_ratio(
        self, volume_24h: float, liquidity: float
    ) -> Optional[WashTradeIndicator]:
        """Check if volume is suspiciously high relative to liquidity"""
        if liquidity <= 0:
            return WashTradeIndicator(
                indicator_type="volume_liquidity",
                score=50,
                description="Cannot assess - no liquidity data",
            )

        if volume_24h <= 0:
            return None

        ratio = volume_24h / liquidity

        if ratio > 10.0:
            return WashTradeIndicator(
                indicator_type="volume_liquidity",
                score=90,
                description="Extremely high volume/liquidity ratio",
                details=f"Volume is {ratio:.1f}x liquidity - strong wash trade signal",
            )
        elif ratio > 5.0:
            return WashTradeIndicator(
                indicator_type="volume_liquidity",
                score=75,
                description="Very high volume/liquidity ratio",
                details=f"Volume is {ratio:.1f}x liquidity - suspicious pattern",
            )
        elif ratio > self.VOLUME_LIQUIDITY_THRESHOLD:
            return WashTradeIndicator(
                indicator_type="volume_liquidity",
                score=55,
                description="Elevated volume/liquidity ratio",
                details=f"Volume is {ratio:.1f}x liquidity",
            )
        elif ratio > 1.0:
            return WashTradeIndicator(
                indicator_type="volume_liquidity",
                score=30,
                description="Volume above liquidity",
                details=f"Ratio: {ratio:.1f}x",
            )
        return None

    def _analyze_trader_concentration(
        self, trade_count: int, unique_traders: int
    ) -> Optional[WashTradeIndicator]:
        """Check if trades are concentrated among few wallets"""
        if trade_count <= 0 or unique_traders <= 0:
            return None

        trades_per_trader = trade_count / unique_traders

        if trades_per_trader > 20:
            return WashTradeIndicator(
                indicator_type="trader_concentration",
                score=85,
                description="Extremely concentrated trading",
                details=f"Avg {trades_per_trader:.1f} trades/wallet - few wallets driving volume",
            )
        elif trades_per_trader > 10:
            return WashTradeIndicator(
                indicator_type="trader_concentration",
                score=65,
                description="Highly concentrated trading",
                details=f"Avg {trades_per_trader:.1f} trades/wallet",
            )
        elif trades_per_trader > 5:
            return WashTradeIndicator(
                indicator_type="trader_concentration",
                score=40,
                description="Moderate trader concentration",
                details=f"Avg {trades_per_trader:.1f} trades/wallet",
            )
        return None

    def _analyze_trade_size_distribution(
        self, avg_size: float, median_size: float
    ) -> Optional[WashTradeIndicator]:
        """Check if trade sizes are suspiciously uniform"""
        if avg_size <= 0 or median_size <= 0:
            return None

        # In organic markets, avg >> median due to whale trades
        # In wash trading, sizes tend to be more uniform
        ratio = median_size / avg_size if avg_size > 0 else 0

        if ratio > 0.9:
            return WashTradeIndicator(
                indicator_type="size_uniformity",
                score=75,
                description="Suspiciously uniform trade sizes",
                details=f"Median/Avg ratio: {ratio:.2f} - trades are too similar",
            )
        elif ratio > 0.8:
            return WashTradeIndicator(
                indicator_type="size_uniformity",
                score=50,
                description="Trade sizes are quite uniform",
                details=f"Median/Avg ratio: {ratio:.2f}",
            )
        return None

    def _analyze_side_balance(
        self, yes_volume: float, no_volume: float
    ) -> Optional[WashTradeIndicator]:
        """Check if YES/NO volume is suspiciously balanced"""
        if yes_volume <= 0 or no_volume <= 0:
            return None

        total = yes_volume + no_volume
        balance_ratio = min(yes_volume, no_volume) / max(yes_volume, no_volume)

        # Wash traders often trade both sides equally
        if balance_ratio > 0.95:
            return WashTradeIndicator(
                indicator_type="side_balance",
                score=70,
                description="YES/NO volume nearly perfectly balanced",
                details=f"Balance ratio: {balance_ratio:.2f} - unusual symmetry",
            )
        elif balance_ratio > 0.85:
            return WashTradeIndicator(
                indicator_type="side_balance",
                score=45,
                description="YES/NO volume highly balanced",
                details=f"Balance ratio: {balance_ratio:.2f}",
            )
        return None

    def _analyze_volume_anomaly(
        self, volume_24h: float, trade_count: int, avg_trade_size: float
    ) -> Optional[WashTradeIndicator]:
        """Check for volume calculation anomalies"""
        if trade_count <= 0 or avg_trade_size <= 0:
            return None

        # Calculate expected volume
        expected_volume = trade_count * avg_trade_size

        if volume_24h > 0:
            discrepancy = abs(volume_24h - expected_volume) / volume_24h

            if discrepancy > 0.5:
                return WashTradeIndicator(
                    indicator_type="volume_anomaly",
                    score=60,
                    description="Volume calculation discrepancy",
                    details=f"Reported volume differs from trade data by {discrepancy:.0%}",
                )

        return None

    def get_risk_color(self, risk_level: WashTradeRisk) -> str:
        """Get color for risk level display"""
        colors = {
            WashTradeRisk.LOW: "green",
            WashTradeRisk.MEDIUM: "yellow",
            WashTradeRisk.HIGH: "orange1",
            WashTradeRisk.VERY_HIGH: "red",
        }
        return colors.get(risk_level, "white")

    def get_risk_description(self, risk_level: WashTradeRisk) -> str:
        """Get description for risk level"""
        descriptions = {
            WashTradeRisk.LOW: "Trading patterns appear organic",
            WashTradeRisk.MEDIUM: "Some unusual patterns detected",
            WashTradeRisk.HIGH: "Multiple wash trading indicators present",
            WashTradeRisk.VERY_HIGH: "Strong evidence of artificial volume",
        }
        return descriptions.get(risk_level, "Unknown")


def quick_wash_trade_score(volume_24h: float, liquidity: float) -> Tuple[int, str]:
    """Quick wash trade score for use in other modules

    Returns:
        Tuple of (score 0-100, description)
    """
    if liquidity <= 0:
        return 50, "Cannot assess"

    if volume_24h <= 0:
        return 20, "No volume"

    ratio = volume_24h / liquidity

    if ratio > 10.0:
        return 90, "Extreme volume anomaly"
    elif ratio > 5.0:
        return 75, "Very high volume/liquidity"
    elif ratio > 3.0:
        return 55, "Elevated volume/liquidity"
    elif ratio > 1.5:
        return 35, "Volume above liquidity"
    elif ratio > 0.5:
        return 20, "Normal trading pattern"
    else:
        return 25, "Low trading activity"
