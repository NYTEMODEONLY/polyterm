"""Statuspage client for status.polymarket.com.

Fetches the documented Statuspage v2 summary JSON. Network or parse
failures return ``status_unknown``. This client never reports operational
unless the page payload explicitly includes ``status.indicator == "none"``.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests


DEFAULT_STATUS_PAGE_URL = "https://status.polymarket.com"
STATUSPAGE_SUMMARY_PATH = "/api/v2/summary.json"

# Statuspage v2 page-level indicators. "none" means all systems operational.
STATUSPAGE_INDICATORS = frozenset(
    {"none", "minor", "major", "critical", "maintenance"}
)


@dataclass
class StatusPageSnapshot:
    """Parsed Statuspage v2 summary, or an honest unknown result."""

    reachable: bool
    indicator: str
    description: str
    page_url: str = DEFAULT_STATUS_PAGE_URL
    page_name: str = ""
    updated_at: str = ""
    components: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "reachable": self.reachable,
            "indicator": self.indicator,
            "description": self.description,
            "page_url": self.page_url,
            "page_name": self.page_name,
            "updated_at": self.updated_at,
            "components": list(self.components),
        }
        if self.error:
            payload["error"] = self.error
        return payload


def unknown_status_snapshot(
    *,
    reachable: bool,
    error: str,
    page_url: str = DEFAULT_STATUS_PAGE_URL,
    description: str = "Status page unreachable or unreadable",
) -> StatusPageSnapshot:
    """Build a snapshot that never claims operational."""
    return StatusPageSnapshot(
        reachable=reachable,
        indicator="status_unknown",
        description=description,
        page_url=page_url,
        error=error,
    )


def parse_statuspage_summary(
    payload: Any,
    *,
    reachable: bool = True,
    page_url: str = DEFAULT_STATUS_PAGE_URL,
) -> StatusPageSnapshot:
    """Parse Statuspage v2 ``/api/v2/summary.json``.

    Operational is only returned when ``status.indicator`` is the documented
    Statuspage value ``none``. Missing, malformed, or unrecognized payloads
    become ``status_unknown``.
    """
    if not isinstance(payload, dict):
        return unknown_status_snapshot(
            reachable=reachable,
            error="Status page payload is not a JSON object",
            page_url=page_url,
        )

    status = payload.get("status")
    if not isinstance(status, dict):
        return unknown_status_snapshot(
            reachable=reachable,
            error="Status page JSON is missing status object",
            page_url=page_url,
        )

    indicator = status.get("indicator")
    if indicator not in STATUSPAGE_INDICATORS:
        return unknown_status_snapshot(
            reachable=reachable,
            error=f"Unrecognized status indicator: {indicator!r}",
            page_url=page_url,
        )

    page = payload.get("page") if isinstance(payload.get("page"), dict) else {}
    description = status.get("description")
    if not isinstance(description, str) or not description.strip():
        description = {
            "none": "All Systems Operational",
            "minor": "Minor Service Outage",
            "major": "Major Service Outage",
            "critical": "Critical Service Outage",
            "maintenance": "Service Under Maintenance",
        }.get(indicator, "Status page report")

    components: List[Dict[str, str]] = []
    raw_components = payload.get("components")
    if isinstance(raw_components, list):
        for item in raw_components:
            if not isinstance(item, dict):
                continue
            name = item.get("name")
            component_status = item.get("status")
            if isinstance(name, str) and isinstance(component_status, str):
                components.append({"name": name, "status": component_status})

    return StatusPageSnapshot(
        reachable=reachable,
        indicator=str(indicator),
        description=description,
        page_url=page.get("url") or page_url,
        page_name=str(page.get("name") or ""),
        updated_at=str(page.get("updated_at") or ""),
        components=components,
    )


class StatusPageClient:
    """Tiny HTTP client for the Polymarket Statuspage v2 summary."""

    def __init__(
        self,
        base_url: str = DEFAULT_STATUS_PAGE_URL,
        timeout: float = 5.0,
        session: Optional[requests.Session] = None,
    ):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = session or requests.Session()
        self._owns_session = session is None

    def get_summary(self) -> StatusPageSnapshot:
        """Fetch ``GET /api/v2/summary.json``.

        Unreachable or unreadable pages return ``status_unknown``. This method
        does not retry: a failed fetch is unknown, not operational.
        """
        url = f"{self.base_url}{STATUSPAGE_SUMMARY_PATH}"
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            try:
                payload = response.json()
            except ValueError as exc:
                return unknown_status_snapshot(
                    reachable=True,
                    error=f"Status page returned non-JSON: {exc}",
                    page_url=self.base_url,
                )
            return parse_statuspage_summary(
                payload,
                reachable=True,
                page_url=self.base_url,
            )
        except requests.exceptions.RequestException as exc:
            return unknown_status_snapshot(
                reachable=False,
                error=str(exc),
                page_url=self.base_url,
            )
        except Exception as exc:
            return unknown_status_snapshot(
                reachable=False,
                error=str(exc),
                page_url=self.base_url,
            )

    def close(self) -> None:
        """Close the HTTP session when this client created it."""
        if self._owns_session:
            self.session.close()
