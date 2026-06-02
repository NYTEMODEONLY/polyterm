"""Unified local alert rule engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..api.gamma import GammaClient
from ..api.market_utils import market_probability_price
from ..db.database import Database
from ..db.models import Alert


@dataclass
class AlertRule:
    """Local alert rule definition."""

    rule_type: str
    market_id: str = ""
    title: str = ""
    above: Optional[float] = None
    below: Optional[float] = None
    severity: int = 50
    enabled: bool = True
    channels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_type": self.rule_type,
            "market_id": self.market_id,
            "title": self.title,
            "above": self.above,
            "below": self.below,
            "severity": self.severity,
            "enabled": self.enabled,
            "channels": self.channels,
            "created_at": self.created_at.isoformat(),
        }


class AlertEngine:
    """Evaluate local alert rules against current market data."""

    def __init__(self, database: Optional[Database] = None, gamma_client: Optional[GammaClient] = None):
        self.db = database or Database()
        self.gamma = gamma_client or GammaClient()

    def create_price_rule(
        self,
        market: str,
        above: Optional[float] = None,
        below: Optional[float] = None,
        severity: int = 50,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Create or preview a local price alert rule."""
        market_data = self._resolve_market(market)
        market_id = str(market_data.get("id") or market)
        title = market_data.get("question") or market_data.get("title") or market
        rule = AlertRule("price", market_id=market_id, title=title, above=above, below=below, severity=severity)
        if dry_run:
            return {"created": False, "dry_run": True, "rule": rule.to_dict()}

        notes = f"agent_rule: above={above} below={below}"
        alert_id = self.db.add_price_alert(
            market_id=market_id,
            title=title,
            target_price=above if above is not None else below if below is not None else 0,
            direction="above" if above is not None else "below",
            notes=notes,
        )
        return {"created": True, "dry_run": False, "rule_id": alert_id, "rule": rule.to_dict()}

    def run_once(self, market: str, above: Optional[float] = None, below: Optional[float] = None) -> Dict[str, Any]:
        """Evaluate a transient price rule once."""
        market_data = self._resolve_market(market)
        price = market_probability_price(market_data)
        triggered = False
        reasons = []
        if above is not None and price >= above:
            triggered = True
            reasons.append(f"price {price:.4f} >= above {above:.4f}")
        if below is not None and price <= below:
            triggered = True
            reasons.append(f"price {price:.4f} <= below {below:.4f}")

        if triggered:
            alert = Alert(
                alert_type="price_rule",
                market_id=str(market_data.get("id") or market),
                severity=60,
                message="; ".join(reasons),
                data={"price": price, "above": above, "below": below},
            )
            self.db.insert_alert(alert)

        return {
            "market": market,
            "price": price,
            "triggered": triggered,
            "reasons": reasons,
            "quality_flags": ["single_scan"],
        }

    def _resolve_market(self, market: str) -> Dict[str, Any]:
        try:
            data = self.gamma.get_market(market)
            if data:
                return data
        except Exception:
            pass
        results = self.gamma.search_markets(market, limit=5)
        for item in results:
            if _is_current_market(item):
                return item
        return results[0] if results else {}


def _is_current_market(market: Dict[str, Any]) -> bool:
    if not market.get("active", True) or market.get("closed", False):
        return False
    end_date = market.get("endDate") or market.get("end_date_iso")
    if not end_date:
        return True
    try:
        parsed = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed > datetime.now(timezone.utc)
    except Exception:
        return True
