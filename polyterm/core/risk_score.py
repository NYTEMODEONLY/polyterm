"""Market Risk Scoring System

Evaluates markets on multiple risk factors to help traders avoid problematic bets.
Risk factors include:
- Resolution clarity (subjective vs objective criteria)
- Liquidity quality (spread, depth)
- Time to resolution
- Historical dispute patterns
- Wash trading indicators
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import re


@dataclass
class RiskAssessment:
    """Risk assessment result for a market"""
    market_id: str
    market_title: str
    overall_grade: str  # A, B, C, D, F
    overall_score: int  # 0-100 (higher = riskier)
    factors: Dict[str, Dict]  # Factor name -> {score, weight, reason}
    warnings: List[str]
    recommendations: List[str]

    def to_dict(self) -> dict:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'overall_grade': self.overall_grade,
            'overall_score': self.overall_score,
            'factors': self.factors,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
        }


class MarketRiskScorer:
    """Scores markets on multiple risk factors"""

    # Risk factor weights (must sum to 1.0)
    WEIGHTS = {
        'resolution_clarity': 0.25,
        'liquidity': 0.20,
        'time_risk': 0.15,
        'volume_quality': 0.15,
        'spread': 0.15,
        'category_risk': 0.10,
    }

    # Subjective/risky keywords in market titles
    SUBJECTIVE_KEYWORDS = [
        'effectively', 'essentially', 'significant', 'major', 'meaningful',
        'substantial', 'largely', 'mainly', 'generally', 'typically',
        'consensus', 'widely', 'broadly', 'most people', 'mainstream',
    ]

    # High-dispute categories
    HIGH_DISPUTE_CATEGORIES = [
        'politics', 'legal', 'regulatory', 'media', 'social',
    ]

    # Low-dispute categories
    LOW_DISPUTE_CATEGORIES = [
        'sports', 'crypto', 'finance', 'weather', 'science',
    ]

    def __init__(self):
        pass

    def score_market(
        self,
        market_id: str,
        title: str,
        description: str = "",
        end_date: Optional[datetime] = None,
        volume_24h: float = 0,
        liquidity: float = 0,
        spread: float = 0,
        category: str = "",
        resolution_source: str = "",
    ) -> RiskAssessment:
        """Score a market's risk level

        Args:
            market_id: Market identifier
            title: Market question/title
            description: Market description/rules
            end_date: When market resolves
            volume_24h: 24-hour trading volume
            liquidity: Total liquidity in market
            spread: Bid-ask spread
            category: Market category
            resolution_source: How resolution is determined

        Returns:
            RiskAssessment with overall grade and factor breakdown
        """
        factors = {}
        warnings = []
        recommendations = []

        # 1. Resolution Clarity Risk
        clarity_score, clarity_reason = self._score_resolution_clarity(
            title, description, resolution_source
        )
        factors['resolution_clarity'] = {
            'score': clarity_score,
            'weight': self.WEIGHTS['resolution_clarity'],
            'reason': clarity_reason,
        }
        if clarity_score >= 60:
            warnings.append("Resolution criteria may be subjective or unclear")
            recommendations.append("Review the exact resolution rules before trading")

        # 2. Liquidity Risk
        liquidity_score, liquidity_reason = self._score_liquidity(liquidity)
        factors['liquidity'] = {
            'score': liquidity_score,
            'weight': self.WEIGHTS['liquidity'],
            'reason': liquidity_reason,
        }
        if liquidity_score >= 60:
            warnings.append("Low liquidity - large orders may cause slippage")
            recommendations.append("Use smaller position sizes or limit orders")

        # 3. Time Risk
        time_score, time_reason = self._score_time_risk(end_date)
        factors['time_risk'] = {
            'score': time_score,
            'weight': self.WEIGHTS['time_risk'],
            'reason': time_reason,
        }
        if time_score >= 60:
            warnings.append("Long time to resolution - capital locked up")

        # 4. Volume Quality
        volume_score, volume_reason = self._score_volume_quality(volume_24h, liquidity)
        factors['volume_quality'] = {
            'score': volume_score,
            'weight': self.WEIGHTS['volume_quality'],
            'reason': volume_reason,
        }
        if volume_score >= 70:
            warnings.append("Volume pattern may indicate wash trading")
            recommendations.append("Verify market activity looks organic")

        # 5. Spread Risk
        spread_score, spread_reason = self._score_spread(spread)
        factors['spread'] = {
            'score': spread_score,
            'weight': self.WEIGHTS['spread'],
            'reason': spread_reason,
        }
        if spread_score >= 50:
            recommendations.append("Use limit orders to avoid paying the spread")

        # 6. Category Risk
        category_score, category_reason = self._score_category(category, title)
        factors['category_risk'] = {
            'score': category_score,
            'weight': self.WEIGHTS['category_risk'],
            'reason': category_reason,
        }
        if category_score >= 60:
            warnings.append("Category has higher historical dispute rate")

        # Calculate overall score
        overall_score = sum(
            factors[k]['score'] * factors[k]['weight']
            for k in factors
        )
        overall_score = int(overall_score)

        # Convert to grade
        overall_grade = self._score_to_grade(overall_score)

        # Add general recommendations based on grade
        if overall_grade in ['D', 'F']:
            recommendations.append("Consider finding a lower-risk alternative")
        if not recommendations:
            recommendations.append("Market appears relatively safe to trade")

        return RiskAssessment(
            market_id=market_id,
            market_title=title,
            overall_grade=overall_grade,
            overall_score=overall_score,
            factors=factors,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _score_resolution_clarity(
        self, title: str, description: str, resolution_source: str
    ) -> Tuple[int, str]:
        """Score how clear/objective the resolution criteria are"""
        score = 0
        reasons = []

        combined_text = f"{title} {description} {resolution_source}".lower()

        # Check for subjective keywords
        subjective_count = sum(
            1 for kw in self.SUBJECTIVE_KEYWORDS if kw in combined_text
        )
        if subjective_count >= 3:
            score += 40
            reasons.append("Multiple subjective terms")
        elif subjective_count >= 1:
            score += 20
            reasons.append("Some subjective language")

        # Check for clear resolution source
        clear_sources = ['official', 'government', 'data', 'api', 'verifiable']
        has_clear_source = any(src in combined_text for src in clear_sources)
        if not has_clear_source:
            score += 25
            reasons.append("No clear resolution source specified")

        # Check for binary clarity (yes/no vs interpretation needed)
        if 'will' not in combined_text and 'does' not in combined_text:
            score += 15
            reasons.append("Question format may need interpretation")

        # Check for specific dates/numbers (more objective)
        has_specific = bool(re.search(r'\d{4}|\d+%|\$\d+', combined_text))
        if has_specific:
            score -= 10  # Reduce risk for specific criteria
            reasons.append("Has specific numeric criteria")

        score = max(0, min(100, score))
        reason = "; ".join(reasons) if reasons else "Resolution appears clear"
        return score, reason

    def _score_liquidity(self, liquidity: float) -> Tuple[int, str]:
        """Score liquidity risk (lower liquidity = higher risk)"""
        if liquidity <= 0:
            return 80, "No liquidity data available"

        if liquidity >= 500000:
            return 0, f"Excellent liquidity (${liquidity:,.0f})"
        elif liquidity >= 100000:
            return 15, f"Good liquidity (${liquidity:,.0f})"
        elif liquidity >= 50000:
            return 30, f"Moderate liquidity (${liquidity:,.0f})"
        elif liquidity >= 10000:
            return 50, f"Low liquidity (${liquidity:,.0f})"
        elif liquidity >= 1000:
            return 70, f"Very low liquidity (${liquidity:,.0f})"
        else:
            return 90, f"Minimal liquidity (${liquidity:,.0f})"

    def _score_time_risk(self, end_date: Optional[datetime]) -> Tuple[int, str]:
        """Score time-to-resolution risk"""
        if end_date is None:
            return 50, "No end date specified"

        now = datetime.now()
        if end_date < now:
            return 0, "Market has ended"

        days_remaining = (end_date - now).days

        if days_remaining <= 1:
            return 10, f"Resolves very soon ({days_remaining} days)"
        elif days_remaining <= 7:
            return 15, f"Resolves soon ({days_remaining} days)"
        elif days_remaining <= 30:
            return 25, f"Resolves within a month ({days_remaining} days)"
        elif days_remaining <= 90:
            return 40, f"Medium-term ({days_remaining} days)"
        elif days_remaining <= 365:
            return 60, f"Long-term ({days_remaining} days)"
        else:
            return 80, f"Very long-term ({days_remaining} days)"

    def _score_volume_quality(
        self, volume_24h: float, liquidity: float
    ) -> Tuple[int, str]:
        """Score volume quality (detect potential wash trading)"""
        if volume_24h <= 0:
            return 40, "No recent volume"

        if liquidity <= 0:
            return 50, "Cannot assess volume quality without liquidity data"

        # Volume to liquidity ratio
        # Normal: volume ~= 10-50% of liquidity per day
        # Suspicious: volume >> liquidity (could be wash trading)
        ratio = volume_24h / liquidity if liquidity > 0 else 0

        if ratio > 5.0:
            return 85, f"Volume/liquidity ratio very high ({ratio:.1f}x) - possible wash trading"
        elif ratio > 2.0:
            return 60, f"Volume/liquidity ratio elevated ({ratio:.1f}x)"
        elif ratio > 0.5:
            return 20, f"Healthy volume/liquidity ratio ({ratio:.1f}x)"
        elif ratio > 0.1:
            return 30, f"Low volume relative to liquidity ({ratio:.1f}x)"
        else:
            return 45, f"Very low trading activity ({ratio:.1f}x)"

    def _score_spread(self, spread: float) -> Tuple[int, str]:
        """Score bid-ask spread risk"""
        if spread <= 0:
            return 50, "No spread data available"

        spread_pct = spread * 100

        if spread_pct <= 1:
            return 0, f"Very tight spread ({spread_pct:.1f}%)"
        elif spread_pct <= 2:
            return 15, f"Good spread ({spread_pct:.1f}%)"
        elif spread_pct <= 5:
            return 35, f"Moderate spread ({spread_pct:.1f}%)"
        elif spread_pct <= 10:
            return 55, f"Wide spread ({spread_pct:.1f}%)"
        else:
            return 80, f"Very wide spread ({spread_pct:.1f}%)"

    def _score_category(self, category: str, title: str) -> Tuple[int, str]:
        """Score category-based risk"""
        cat_lower = category.lower() if category else ""
        title_lower = title.lower()

        # Check explicit category
        for high_risk in self.HIGH_DISPUTE_CATEGORIES:
            if high_risk in cat_lower or high_risk in title_lower:
                return 60, f"Higher dispute rate in {high_risk} category"

        for low_risk in self.LOW_DISPUTE_CATEGORIES:
            if low_risk in cat_lower or low_risk in title_lower:
                return 15, f"Lower dispute rate in {low_risk} category"

        return 35, "Average category risk"

    def _score_to_grade(self, score: int) -> str:
        """Convert numeric score to letter grade"""
        if score <= 20:
            return 'A'  # Low risk
        elif score <= 35:
            return 'B'  # Moderate-low risk
        elif score <= 50:
            return 'C'  # Moderate risk
        elif score <= 70:
            return 'D'  # High risk
        else:
            return 'F'  # Very high risk

    def get_grade_description(self, grade: str) -> str:
        """Get human-readable description of grade"""
        descriptions = {
            'A': "Low Risk - Clear resolution, good liquidity",
            'B': "Moderate-Low Risk - Generally safe with minor concerns",
            'C': "Moderate Risk - Some concerns, trade with caution",
            'D': "High Risk - Multiple concerns, proceed carefully",
            'F': "Very High Risk - Consider avoiding this market",
        }
        return descriptions.get(grade, "Unknown")

    def get_grade_color(self, grade: str) -> str:
        """Get Rich color for grade"""
        colors = {
            'A': 'green',
            'B': 'bright_green',
            'C': 'yellow',
            'D': 'orange1',
            'F': 'red',
        }
        return colors.get(grade, 'white')
