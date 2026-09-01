"""UMA oracle helpers: honest Gamma resolution snapshots, plus optional risk analysis.

Watch uses ``snapshot_market_resolution`` only. That path copies Gamma/CLOB
fields that exist (disputed, proposed, timestamps, trading flags) and omits
the rest. It does not invent a fairness score or letter grade.

``UMADisputeTracker.analyze_resolution_risk`` is a separate heuristic used by
``polyterm risk``. Watch does not call it.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


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

        # Normalize both to naive datetimes to avoid timezone mismatch
        if end_date.tzinfo is not None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            # Compare both as UTC
            days_until = (end_date - now).days
        else:
            now = datetime.now()
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


# Honest watch snapshot. Never a fairness / letter grade.
KNOWN_UMA_STATUSES = frozenset({"none", "pending", "proposed", "disputed", "resolved"})
UMA_IN_ORACLE = frozenset({"pending", "proposed", "disputed"})
PROPOSER_KEYS = ("proposer", "proposedBy", "proposed_by", "proposerAddress")
GRADE_FIELDS = frozenset({
    "risk_level",
    "risk_score",
    "grade",
    "overall_grade",
    "fairness",
    "fairness_score",
})


def snapshot_market_resolution(
    market: Optional[Mapping[str, Any]],
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Copy UMA/resolution fields from one Gamma (or CLOB) market dict.

    Missing fields are omitted. Unparseable timestamps do not become a
    countdown. No UMA data is ``status=none`` plus ``uma_unavailable``.
    """
    flags: List[str] = []
    if not isinstance(market, dict):
        return {
            "status": "none",
            "disputed": False,
            "quality_flags": ["uma_unavailable"],
        }

    raw_status = _scalar_text(_first(market, "umaResolutionStatus", "uma_resolution_status"))
    statuses, statuses_malformed = _parse_status_list(
        _first(market, "umaResolutionStatuses", "uma_resolution_statuses")
    )
    if statuses_malformed:
        flags.append("malformed_uma_fields")

    status = _current_uma_status(raw_status, statuses)
    if status == "none":
        flags.append("uma_unavailable")

    payload: Dict[str, Any] = {
        "status": status,
        "disputed": status == "disputed",
        "source": "gamma",
    }
    if raw_status:
        payload["uma_resolution_status"] = raw_status
    if statuses is not None:
        payload["uma_resolution_statuses"] = statuses

    proposer = _scalar_text(_first(market, *PROPOSER_KEYS))
    if proposer:
        payload["proposer"] = proposer

    resolved_by = _scalar_text(_first(market, "resolvedBy", "resolved_by"))
    if resolved_by:
        payload["resolved_by"] = resolved_by

    accepting, accepting_present = _optional_bool(
        market, "acceptingOrders", "accepting_orders"
    )
    if accepting_present:
        if accepting is None:
            flags.append("malformed_uma_fields")
        else:
            payload["accepting_orders"] = accepting

    closed, closed_present = _optional_bool(market, "closed")
    if closed_present:
        if closed is None:
            flags.append("malformed_uma_fields")
        else:
            payload["closed"] = closed

    active, active_present = _optional_bool(market, "active")
    if active_present and active is not None:
        payload["active"] = active

    auto_resolved, auto_present = _optional_bool(
        market, "automaticallyResolved", "automatically_resolved"
    )
    if auto_present and auto_resolved is not None:
        payload["automatically_resolved"] = auto_resolved

    trading = _trading_state(payload)
    if trading:
        payload["trading"] = trading
    redeemable = _redeemable_state(payload)
    if redeemable is not None:
        payload["redeemable"] = redeemable

    raw_end = _first(market, "umaEndDate", "uma_end_date", "umaEndDateIso", "uma_end_date_iso")
    uma_end = _parse_timestamp(raw_end)
    if raw_end not in (None, "") and uma_end is None:
        flags.append("unparsed_timestamp")
    elif uma_end is not None:
        payload["uma_end_date"] = uma_end.isoformat()
        clock = _as_utc(now) or datetime.now(timezone.utc)
        hours = (uma_end - clock).total_seconds() / 3600.0
        if hours > 0:
            payload["hours_remaining"] = round(hours, 2)
        else:
            payload["hours_since_uma_end"] = round(abs(hours), 2)

    if status in UMA_IN_ORACLE and "hours_remaining" not in payload:
        flags.append("missing_timestamps")

    liveness = _optional_number(_first(market, "customLiveness", "custom_liveness"))
    if liveness is not None:
        payload["liveness_seconds"] = liveness

    payload["quality_flags"] = _unique_flags(flags)
    for key in GRADE_FIELDS:
        payload.pop(key, None)
    return payload


def resolution_dashboard_line(snapshot: Optional[Mapping[str, Any]]) -> str:
    """One short watch-header line. Empty snapshot is an empty string."""
    if not isinstance(snapshot, Mapping):
        return ""
    status = str(snapshot.get("status") or "none")
    parts = [f"UMA: {status}"]
    if snapshot.get("proposer"):
        parts.append(f"proposer={snapshot['proposer']}")
    hours = snapshot.get("hours_remaining")
    if isinstance(hours, (int, float)):
        parts.append(f"{hours:g}h remaining")
    elif status in UMA_IN_ORACLE:
        parts.append("window unknown")
    trading = snapshot.get("trading")
    if trading == "open_for_trading":
        parts.append("open for trading")
    elif trading == "not_accepting_orders":
        parts.append("not accepting orders")
    elif trading == "closed":
        parts.append("closed")
    if snapshot.get("redeemable") is True:
        parts.append("redeemable")
    flags = snapshot.get("quality_flags") or []
    if "uma_unavailable" in flags:
        parts.append("uma unavailable")
    return " | ".join(parts)


def _first(market: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in market and market[key] not in (None, ""):
            return market[key]
    return None


def _scalar_text(value: Any) -> Optional[str]:
    if value is None or isinstance(value, (dict, list, tuple)):
        return None
    text = str(value).strip()
    return text or None


def _parse_status_list(value: Any) -> Tuple[Optional[List[str]], bool]:
    if value is None or value == "":
        return None, False
    if isinstance(value, (list, tuple)):
        return _normalize_status_items(value), False
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return [], False
        if text.startswith("[") or text.startswith("{"):
            try:
                parsed = json.loads(text)
            except (json.JSONDecodeError, TypeError, ValueError):
                return None, True
            if isinstance(parsed, list):
                return _normalize_status_items(parsed), False
            return None, True
        return _normalize_status_items([text]), False
    return None, True


def _normalize_status_items(items: Sequence[Any]) -> List[str]:
    out: List[str] = []
    for item in items:
        text = _scalar_text(item)
        if text:
            out.append(text.lower())
    return out


def _current_uma_status(
    raw_status: Optional[str],
    statuses: Optional[Sequence[str]],
) -> str:
    if raw_status:
        lowered = raw_status.lower()
        if lowered in KNOWN_UMA_STATUSES:
            return lowered
        if "disput" in lowered:
            return "disputed"
        if "propos" in lowered:
            return "proposed"
        if lowered in {"resolved", "settled"}:
            return "resolved"
        if "pend" in lowered:
            return "pending"
    if statuses:
        if any("disput" in item for item in statuses):
            return "disputed"
        if any("propos" in item for item in statuses):
            return "proposed"
        if any(item in {"resolved", "settled"} for item in statuses):
            return "resolved"
        if any("pend" in item for item in statuses):
            return "pending"
    return "none"


def _optional_bool(market: Mapping[str, Any], *keys: str) -> Tuple[Optional[bool], bool]:
    for key in keys:
        if key not in market:
            continue
        value = market[key]
        if isinstance(value, bool):
            return value, True
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            return value.strip().lower() == "true", True
        return None, True
    return None, False


def _optional_number(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:  # NaN
        return None
    return number


def _parse_timestamp(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Only treat values that look like unix seconds/ms as timestamps.
        if value > 1_000_000_000_000:
            value = value / 1000.0
        if value > 1_000_000_000:
            try:
                return datetime.fromtimestamp(float(value), tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        return None
    text = str(value).strip()
    if not text:
        return None
    text = text.replace("Z", "+00:00")
    if text.endswith("+00"):
        text = text + ":00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return _as_utc(parsed)


def _as_utc(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _trading_state(payload: Mapping[str, Any]) -> Optional[str]:
    closed = payload.get("closed")
    accepting = payload.get("accepting_orders")
    if closed is True:
        return "closed"
    if accepting is True:
        return "open_for_trading"
    if accepting is False:
        return "not_accepting_orders"
    return None


def _redeemable_state(payload: Mapping[str, Any]) -> Optional[bool]:
    status = payload.get("status")
    closed = payload.get("closed")
    auto = payload.get("automatically_resolved")
    if status in UMA_IN_ORACLE:
        return False
    if closed is True and (status == "resolved" or auto is True):
        return True
    if closed is False:
        return False
    if status == "resolved":
        return True
    return None


def _unique_flags(flags: Iterable[str]) -> List[str]:
    out: List[str] = []
    seen = set()
    for flag in flags:
        if not flag or flag in seen:
            continue
        seen.add(flag)
        out.append(flag)
    return out
