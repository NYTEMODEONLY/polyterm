"""UMA Oracle Dispute Tracker - Monitor market resolution disputes"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
from enum import Enum


class DisputeStatus(Enum):
    """Status of a UMA dispute"""
    NONE = "none"  # No dispute
    PENDING = "pending"  # Dispute period open
    DISPUTED = "disputed"  # Active dispute
    RESOLVED_ORIGINAL = "resolved_original"  # Dispute resolved in favor of original answer
    RESOLVED_DISPUTED = "resolved_disputed"  # Dispute resolved in favor of disputant
    TIMEOUT = "timeout"  # Dispute period expired


class ResolutionRisk(Enum):
    """Risk level for market resolution"""
    LOW = "low"  # Clear, objective criteria
    MEDIUM = "medium"  # Some subjectivity
    HIGH = "high"  # Highly subjective or controversial
    VERY_HIGH = "very_high"  # History of disputes in category


@dataclass
class UMADispute:
    """Represents a UMA oracle dispute"""
    market_id: str
    market_title: str
    proposed_answer: str
    dispute_reason: Optional[str]
    status: DisputeStatus
    proposed_at: datetime
    dispute_deadline: Optional[datetime]
    bond_amount: float
    disputed_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    final_answer: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'proposed_answer': self.proposed_answer,
            'dispute_reason': self.dispute_reason,
            'status': self.status.value,
            'proposed_at': self.proposed_at.isoformat() if self.proposed_at else None,
            'dispute_deadline': self.dispute_deadline.isoformat() if self.dispute_deadline else None,
            'bond_amount': self.bond_amount,
            'disputed_at': self.disputed_at.isoformat() if self.disputed_at else None,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'final_answer': self.final_answer,
        }


@dataclass
class ResolutionAnalysis:
    """Analysis of market resolution risk"""
    market_id: str
    market_title: str
    risk_level: ResolutionRisk
    risk_score: int  # 0-100
    factors: Dict[str, dict]
    warnings: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            'market_id': self.market_id,
            'market_title': self.market_title,
            'risk_level': self.risk_level.value,
            'risk_score': self.risk_score,
            'factors': self.factors,
            'warnings': self.warnings,
            'recommendations': self.recommendations,
        }


class UMADisputeTracker:
    """Track and analyze UMA oracle disputes"""

    # Keywords that indicate higher dispute risk
    SUBJECTIVE_KEYWORDS = [
        'best', 'most', 'significant', 'major', 'meaningful',
        'substantial', 'successful', 'effective', 'important',
        'controversial', 'unprecedented', 'historic', 'notable',
    ]

    # Categories with historical dispute issues
    HIGH_RISK_CATEGORIES = [
        'politics', 'government', 'regulation', 'legal',
        'controversial', 'opinion', 'social',
    ]

    # Resolution sources that are more reliable
    RELIABLE_SOURCES = [
        'associated press', 'ap news', 'reuters', 'official government',
        'official results', 'blockchain', 'oracle', 'on-chain',
        'official statistics', 'official announcement',
    ]

    def __init__(self):
        # Simulated dispute data (in production, would fetch from UMA API)
        self.active_disputes: List[UMADispute] = []
        self.historical_disputes: List[UMADispute] = []

    def analyze_resolution_risk(
        self,
        market_id: str,
        title: str,
        description: str,
        category: str = "",
        resolution_source: str = "",
        end_date: Optional[datetime] = None,
    ) -> ResolutionAnalysis:
        """Analyze market for resolution dispute risk"""

        factors = {}
        warnings = []
        recommendations = []
        total_score = 0
        total_weight = 0

        # Factor 1: Subjective language in title/description (30% weight)
        subjectivity_score, subjectivity_details = self._score_subjectivity(title, description)
        factors['subjectivity'] = {
            'score': subjectivity_score,
            'weight': 0.30,
            'details': subjectivity_details,
        }
        total_score += subjectivity_score * 0.30
        total_weight += 0.30

        if subjectivity_score > 50:
            warnings.append("Title contains subjective language that could lead to disputes")
            recommendations.append("Look for markets with more objective resolution criteria")

        # Factor 2: Category risk (20% weight)
        category_score, category_details = self._score_category_risk(category)
        factors['category'] = {
            'score': category_score,
            'weight': 0.20,
            'details': category_details,
        }
        total_score += category_score * 0.20
        total_weight += 0.20

        if category_score > 60:
            warnings.append(f"Category '{category}' has historically higher dispute rates")

        # Factor 3: Resolution source clarity (25% weight)
        source_score, source_details = self._score_resolution_source(resolution_source, description)
        factors['resolution_source'] = {
            'score': source_score,
            'weight': 0.25,
            'details': source_details,
        }
        total_score += source_score * 0.25
        total_weight += 0.25

        if source_score > 50:
            warnings.append("Resolution source is unclear or potentially disputed")
            recommendations.append("Prefer markets with official, verifiable resolution sources")

        # Factor 4: Time to resolution (15% weight)
        time_score, time_details = self._score_time_risk(end_date)
        factors['time_risk'] = {
            'score': time_score,
            'weight': 0.15,
            'details': time_details,
        }
        total_score += time_score * 0.15
        total_weight += 0.15

        if time_score > 70:
            warnings.append("Long time until resolution increases uncertainty")

        # Factor 5: Description clarity (10% weight)
        clarity_score, clarity_details = self._score_description_clarity(description)
        factors['description_clarity'] = {
            'score': clarity_score,
            'weight': 0.10,
            'details': clarity_details,
        }
        total_score += clarity_score * 0.10
        total_weight += 0.10

        if clarity_score > 60:
            recommendations.append("Review resolution criteria carefully before trading")

        # Calculate overall score
        overall_score = int(total_score / total_weight) if total_weight > 0 else 50

        # Determine risk level
        if overall_score <= 25:
            risk_level = ResolutionRisk.LOW
        elif overall_score <= 45:
            risk_level = ResolutionRisk.MEDIUM
        elif overall_score <= 65:
            risk_level = ResolutionRisk.HIGH
        else:
            risk_level = ResolutionRisk.VERY_HIGH

        # Add general recommendations
        if not recommendations:
            recommendations.append("Resolution criteria appear clear")

        if risk_level in [ResolutionRisk.HIGH, ResolutionRisk.VERY_HIGH]:
            recommendations.append("Consider position sizing carefully due to dispute risk")
            recommendations.append("Monitor UMA oracle for any proposed answers")

        return ResolutionAnalysis(
            market_id=market_id,
            market_title=title,
            risk_level=risk_level,
            risk_score=overall_score,
            factors=factors,
            warnings=warnings,
            recommendations=recommendations,
        )

    def _score_subjectivity(self, title: str, description: str) -> tuple:
        """Score based on subjective language"""
        text = f"{title} {description}".lower()

        found_keywords = []
        for keyword in self.SUBJECTIVE_KEYWORDS:
            if keyword in text:
                found_keywords.append(keyword)

        if not found_keywords:
            return 15, "No subjective language detected"
        elif len(found_keywords) == 1:
            return 40, f"Contains subjective term: '{found_keywords[0]}'"
        elif len(found_keywords) <= 3:
            return 65, f"Multiple subjective terms: {', '.join(found_keywords[:3])}"
        else:
            return 85, f"Highly subjective language ({len(found_keywords)} terms)"

    def _score_category_risk(self, category: str) -> tuple:
        """Score based on category historical dispute rate"""
        category_lower = category.lower() if category else ""

        for high_risk in self.HIGH_RISK_CATEGORIES:
            if high_risk in category_lower:
                return 70, f"Category '{category}' has higher dispute history"

        if category_lower in ['crypto', 'sports', 'finance']:
            return 25, f"Category '{category}' typically has objective outcomes"
        elif category_lower:
            return 40, f"Category '{category}' has moderate dispute history"
        else:
            return 50, "No category specified"

    def _score_resolution_source(self, resolution_source: str, description: str) -> tuple:
        """Score based on resolution source reliability"""
        combined = f"{resolution_source} {description}".lower()

        for reliable in self.RELIABLE_SOURCES:
            if reliable in combined:
                return 20, f"Uses reliable source: {reliable}"

        if 'official' in combined:
            return 30, "References official sources"
        elif resolution_source:
            return 50, f"Resolution source: {resolution_source[:50]}"
        else:
            return 75, "No clear resolution source specified"

    def _score_time_risk(self, end_date: Optional[datetime]) -> tuple:
        """Score based on time to resolution"""
        if not end_date:
            return 50, "No end date specified"

        now = datetime.now(end_date.tzinfo) if end_date.tzinfo else datetime.now()
        days_until = (end_date - now).days

        if days_until < 0:
            return 30, "Market has ended"
        elif days_until <= 7:
            return 20, f"Resolves within {days_until} days"
        elif days_until <= 30:
            return 35, f"Resolves within {days_until} days"
        elif days_until <= 90:
            return 50, f"Resolves in ~{days_until // 30} months"
        elif days_until <= 365:
            return 70, f"Resolves in ~{days_until // 30} months"
        else:
            return 85, f"Long resolution period ({days_until} days)"

    def _score_description_clarity(self, description: str) -> tuple:
        """Score based on description clarity"""
        if not description:
            return 80, "No description provided"

        desc_len = len(description)

        # Check for clear resolution criteria
        clarity_indicators = [
            'will resolve', 'resolves to', 'resolution criteria',
            'determined by', 'based on', 'according to',
        ]

        has_criteria = any(ind in description.lower() for ind in clarity_indicators)

        if desc_len < 50:
            return 70, "Very short description"
        elif desc_len < 150 and not has_criteria:
            return 55, "Short description without clear criteria"
        elif has_criteria:
            return 20, "Clear resolution criteria stated"
        else:
            return 40, "Adequate description"

    def get_risk_color(self, risk_level: ResolutionRisk) -> str:
        """Get color for risk level display"""
        colors = {
            ResolutionRisk.LOW: "green",
            ResolutionRisk.MEDIUM: "yellow",
            ResolutionRisk.HIGH: "orange1",
            ResolutionRisk.VERY_HIGH: "red",
        }
        return colors.get(risk_level, "white")

    def get_risk_description(self, risk_level: ResolutionRisk) -> str:
        """Get description for risk level"""
        descriptions = {
            ResolutionRisk.LOW: "Clear resolution criteria, low dispute risk",
            ResolutionRisk.MEDIUM: "Some subjectivity, moderate dispute risk",
            ResolutionRisk.HIGH: "Significant dispute risk, trade with caution",
            ResolutionRisk.VERY_HIGH: "High dispute risk, careful position sizing recommended",
        }
        return descriptions.get(risk_level, "Unknown risk level")
