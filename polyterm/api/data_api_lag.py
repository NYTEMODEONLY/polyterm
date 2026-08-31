"""Labels for Polymarket Data API wallet, positions, activity, and trades.

Those surfaces are lagged. They are not the live CLOB fill tape.
Do not invent a lag duration.
"""

from typing import Any, Dict, Iterable, List, Mapping, MutableMapping, Optional


SOURCE = "data_api"
LAGGED = True
QUALITY_FLAG = "lagged_data_api"
LIVE_MISNOMER = "live_data_api_trades"

DISCLOSURE = (
    "Lagged Data API (not live CLOB). Wallet, positions, activity, and trades "
    "from data-api.polymarket.com are not the live CLOB fill tape."
)


def metadata() -> Dict[str, Any]:
    """JSON fields that mark a payload as lagged Data API data."""
    return {
        "source": SOURCE,
        "lag": True,
        "lagged": True,
    }


def table_title(title: str) -> str:
    """Append an explicit lagged banner to a table title."""
    return f"{title} — lagged Data API (not live CLOB)"


def with_quality_flag(flags: Optional[Iterable[str]] = None) -> List[str]:
    """Return quality flags with the lagged Data API marker, without a live-CLOB misnomer."""
    out: List[str] = []
    seen = set()
    for flag in flags or []:
        if not flag or flag == LIVE_MISNOMER or flag in seen:
            continue
        out.append(flag)
        seen.add(flag)
    if QUALITY_FLAG not in seen:
        out.insert(0, QUALITY_FLAG)
    return out


def stamp(payload: Mapping[str, Any]) -> Dict[str, Any]:
    """Add `lag=true` / `lagged=true` without inventing a lag duration.

    Nested `source` maps (wallet profile provenance) are left intact.
    Missing string `source` is filled with `data_api`.
    """
    stamped: Dict[str, Any] = dict(payload)
    stamped["lag"] = True
    stamped["lagged"] = True
    source = stamped.get("source")
    if source is None:
        stamped["source"] = SOURCE
    return stamped


def label_payload(
    payload: Mapping[str, Any],
    quality_flags: Optional[Iterable[str]] = None,
) -> Dict[str, Any]:
    """Stamp lag fields and attach the lagged Data API quality flag when flags are present."""
    stamped = stamp(payload)
    flags = quality_flags
    if flags is None:
        existing = stamped.get("quality_flags")
        flags = existing if isinstance(existing, list) else None
    if flags is not None:
        stamped["quality_flags"] = with_quality_flag(flags)
    return stamped


def is_lagged_payload(payload: MutableMapping[str, Any] | Mapping[str, Any]) -> bool:
    """True when a mapping is explicitly labeled lagged Data API."""
    if payload.get("lagged") is True or payload.get("lag") is True:
        return True
    flags = payload.get("quality_flags") or []
    return QUALITY_FLAG in flags
