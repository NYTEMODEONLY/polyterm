"""Combine Statuspage, Gamma, and CLOB probes into an honest health report.

Rules:
- Gamma and CLOB both raising is an outage (same honesty as APIAggregator).
- One of Gamma/CLOB raising is degraded.
- Status page unreachable or unreadable is ``status_unknown``, never operational.
- CLOB trading flags are passed through only when the CLOB payload has them.
  PolyTerm does not invent ``cancel_only`` or ``delayed``.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from ..api.status import StatusPageClient, StatusPageSnapshot, unknown_status_snapshot


@dataclass
class SourceProbe:
    """Result of probing one live API."""

    name: str
    ok: bool
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {"name": self.name, "ok": self.ok}
        if self.error:
            payload["error"] = self.error
        return payload


@dataclass
class ServiceHealth:
    """Combined Polymarket service health for watch and similar surfaces."""

    mode: str
    status: str
    message: str
    gamma: SourceProbe
    clob: SourceProbe
    status_page: StatusPageSnapshot

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode,
            "status": self.status,
            "message": self.message,
            "gamma": self.gamma.to_dict(),
            "clob": self.clob.to_dict(),
            "status_page": self.status_page.to_dict(),
        }


def probe_gamma(gamma_client: Any) -> SourceProbe:
    """Probe Gamma with an existing list call. Empty success is still ok."""
    try:
        gamma_client.get_markets(limit=1, active=True, closed=False)
        return SourceProbe(name="gamma", ok=True)
    except Exception as exc:
        return SourceProbe(name="gamma", ok=False, error=str(exc))


def probe_clob(clob_client: Any) -> SourceProbe:
    """Probe CLOB with sampling-markets. Empty success is still ok."""
    try:
        clob_client.get_current_markets(limit=1)
        return SourceProbe(name="clob", ok=True)
    except Exception as exc:
        return SourceProbe(name="clob", ok=False, error=str(exc))


def clob_trading_flags(market: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Pass through CLOB-native trading fields only.

    CLOB sampling-markets may include ``accepting_orders``. That key is copied
    when present. ``cancel_only`` and ``delayed`` are not synthesized.
    """
    if not isinstance(market, dict):
        return {}
    flags: Dict[str, Any] = {}
    if "accepting_orders" in market:
        flags["accepting_orders"] = market["accepting_orders"]
    return flags


def _page_mode(snapshot: StatusPageSnapshot) -> str:
    """Map a parsed Statuspage indicator onto combiner modes."""
    if snapshot.indicator == "status_unknown":
        return "status_unknown"
    if snapshot.indicator in {"major", "critical"}:
        return "outage"
    if snapshot.indicator in {"minor", "maintenance"}:
        return "degraded"
    if snapshot.indicator == "none":
        return "operational"
    return "status_unknown"


def combine_health(
    gamma: SourceProbe,
    clob: SourceProbe,
    status_page: StatusPageSnapshot,
) -> ServiceHealth:
    """Combine live API probes with the Statuspage snapshot.

    Live API failures take precedence over a green status page. A missing
    status page never upgrades the result to operational.
    """
    if not gamma.ok and not clob.ok:
        message = "Gamma and CLOB both failed to return live data."
        details = []
        if gamma.error:
            details.append(f"gamma={gamma.error}")
        if clob.error:
            details.append(f"clob={clob.error}")
        if details:
            message = f"{message} {'; '.join(details)}"
        return ServiceHealth(
            mode="outage",
            status="outage",
            message=message,
            gamma=gamma,
            clob=clob,
            status_page=status_page,
        )

    if not gamma.ok or not clob.ok:
        down = "Gamma" if not gamma.ok else "CLOB"
        error = gamma.error if not gamma.ok else clob.error
        message = f"{down} failed while the other API responded."
        if error:
            message = f"{message} {down.lower()}={error}"
        return ServiceHealth(
            mode="degraded",
            status="degraded",
            message=message,
            gamma=gamma,
            clob=clob,
            status_page=status_page,
        )

    page_mode = _page_mode(status_page)
    if page_mode == "outage":
        message = (
            status_page.description
            or "Status page reports a major or critical incident."
        )
        return ServiceHealth(
            mode="outage",
            status="outage",
            message=message,
            gamma=gamma,
            clob=clob,
            status_page=status_page,
        )
    if page_mode == "degraded":
        message = status_page.description or "Status page reports a partial incident."
        return ServiceHealth(
            mode="degraded",
            status="degraded",
            message=message,
            gamma=gamma,
            clob=clob,
            status_page=status_page,
        )
    if page_mode == "status_unknown":
        error = status_page.error or "Status page unreachable or unreadable"
        return ServiceHealth(
            mode="status_unknown",
            status="status_unknown",
            message=error,
            gamma=gamma,
            clob=clob,
            status_page=status_page,
        )

    return ServiceHealth(
        mode="operational",
        status="operational",
        message=status_page.description or "All Systems Operational",
        gamma=gamma,
        clob=clob,
        status_page=status_page,
    )


def assess_service_health(
    gamma_client: Any,
    clob_client: Any,
    status_client: Optional[StatusPageClient] = None,
) -> ServiceHealth:
    """Probe Gamma, CLOB, and the status page, then combine the results."""
    gamma = probe_gamma(gamma_client)
    clob = probe_clob(clob_client)
    if status_client is None:
        status_page = unknown_status_snapshot(
            reachable=False,
            error="No status page client provided",
        )
    else:
        status_page = status_client.get_summary()
    return combine_health(gamma, clob, status_page)
