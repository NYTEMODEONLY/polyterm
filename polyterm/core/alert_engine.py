"""Unified local alert rule engine."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..api.data_api_lag import label_payload, with_quality_flag
from ..api.gamma import GammaClient
from ..api.market_utils import market_probability_price
from ..db.database import Database
from ..db.models import Alert
from .print_scanner import PrintScanner, print_message


@dataclass
class AlertRule:
    """Local alert rule definition."""

    rule_type: str
    market_id: str = ""
    title: str = ""
    above: Optional[float] = None
    below: Optional[float] = None
    min_notional: Optional[float] = None
    wallet: str = ""
    severity: int = 50
    enabled: bool = True
    channels: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        payload = {
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
        if self.min_notional is not None:
            payload["min_notional"] = self.min_notional
        if self.wallet:
            payload["wallet"] = self.wallet
        return payload


class AlertEngine:
    """Evaluate local alert rules against current market data."""

    def __init__(
        self,
        database: Optional[Database] = None,
        gamma_client: Optional[GammaClient] = None,
        print_scanner: Optional[PrintScanner] = None,
    ):
        self.db = database or Database()
        self.gamma = gamma_client or GammaClient()
        self.print_scanner = print_scanner or PrintScanner()

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

    def create_print_rule(
        self,
        min_notional,
        market=None,
        wallet=None,
        severity=50,
        dry_run=False,
    ):
        """Create or preview a local print rule on lagged Data API fills."""
        if min_notional is None:
            raise ValueError("min_notional is required for a print rule")
        try:
            min_notional = float(min_notional)
        except (TypeError, ValueError):
            raise ValueError("min_notional must be a number")
        if min_notional < 0:
            raise ValueError("min_notional must be >= 0")

        market_id = str(market).strip() if market else ""
        wallet_address = str(wallet).strip() if wallet else ""
        title = "print min_notional={}".format(min_notional)
        if market_id:
            title = "{} market={}".format(title, market_id)
        if wallet_address:
            title = "{} wallet={}".format(title, wallet_address)

        rule = AlertRule(
            "print",
            market_id=market_id,
            title=title,
            min_notional=min_notional,
            wallet=wallet_address,
            severity=severity,
        )
        result = {
            "created": False,
            "dry_run": True,
            "rule": rule.to_dict(),
            "quality_flags": [],
        }
        if dry_run:
            return label_payload(result)

        rule_id = self.db.add_alert_rule(
            rule_type="print",
            market_id=market_id,
            wallet_address=wallet_address,
            title=title,
            min_notional=min_notional,
            severity=severity,
            notes="agent_rule: print min_notional={} market={} wallet={}".format(
                min_notional, market_id, wallet_address
            ),
        )
        result["created"] = True
        result["dry_run"] = False
        result["rule_id"] = rule_id
        return label_payload(result)

    def run_once(
        self,
        market: str,
        above: Optional[float] = None,
        below: Optional[float] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
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

        if triggered and not dry_run:
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
            "dry_run": dry_run,
            "quality_flags": ["single_scan"],
        }

    def run_print_once(
        self,
        min_notional,
        market=None,
        wallet=None,
        limit=20,
        dry_run=False,
        severity=50,
    ):
        """Evaluate a transient print rule against lagged Data API fills."""
        scan = self.print_scanner.scan(
            min_notional=min_notional,
            market=market,
            wallet=wallet,
            limit=limit,
        )
        prints = scan.get("prints") or []
        triggered = bool(prints)
        alerts = []
        for print_row in prints:
            alert = Alert(
                alert_type="print",
                market_id=str(
                    print_row.get("market_id")
                    or print_row.get("condition_id")
                    or print_row.get("market_slug")
                    or market
                    or ""
                ),
                wallet_address=str(print_row.get("wallet") or ""),
                severity=severity,
                message=print_message(print_row, min_notional=min_notional),
                data=label_payload({
                    "print": print_row,
                    "min_notional": min_notional,
                    "market": market,
                    "wallet": wallet,
                    "quality_flags": with_quality_flag(["single_scan"]),
                }),
            )
            if not dry_run:
                alert.id = self.db.insert_alert(alert)
            alerts.append(alert.to_dict())

        quality_flags = list(scan.get("quality_flags") or [])
        quality_flags.append("single_scan")
        if dry_run:
            quality_flags.append("dry_run")

        return label_payload({
            "rule_type": "print",
            "min_notional": min_notional,
            "market": market,
            "wallet": wallet,
            "fetched": scan.get("fetched", 0),
            "skipped": scan.get("skipped", 0),
            "matched": scan.get("matched", len(prints)),
            "triggered": triggered,
            "dry_run": dry_run,
            "prints": prints,
            "alerts": alerts,
            "quality_flags": quality_flags,
        })

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
