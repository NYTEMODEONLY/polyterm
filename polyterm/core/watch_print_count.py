"""Session lagged-print count for one polyterm watch process.

Counts real Data API prints already on the watch tape. This is not a
second scanner and does not fetch. Empty tape is 0. Missing wallets
and notionals stay missing.
"""

from typing import Any, Dict, List, Mapping, Optional, Set

SESSION_COUNT_KEY = "session_count"


def print_rows_from_payload(prints_payload: Any) -> List[Dict[str, Any]]:
    """Real print dicts already on the tape. Empty tape is []."""
    if not isinstance(prints_payload, Mapping):
        return []
    rows = prints_payload.get("prints")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def payload_print_count(prints_payload: Any) -> int:
    """How many real prints are in this payload. Empty tape is 0."""
    return len(print_rows_from_payload(prints_payload))


def _print_id(row: Mapping[str, Any]) -> str:
    from .watch_loop import print_event_id

    return print_event_id(row)


class WatchPrintSession:
    """Unique lagged prints seen while this watch process is open."""

    def __init__(self) -> None:
        self._ids: Set[str] = set()

    def note(self, prints_payload: Any) -> int:
        """Record real tape rows already shown. Returns the session count."""
        for row in print_rows_from_payload(prints_payload):
            self._ids.add(_print_id(row))
        return self.count

    @property
    def count(self) -> int:
        return len(self._ids)


def stamp_session_print_count(
    prints_payload: Any,
    session: Optional[WatchPrintSession] = None,
) -> Dict[str, Any]:
    """Copy the payload and stamp session_count from real tape rows."""
    if isinstance(prints_payload, Mapping):
        payload = dict(prints_payload)
    else:
        payload = {"prints": [], "count": 0}
    if session is None:
        payload[SESSION_COUNT_KEY] = payload_print_count(payload)
    else:
        payload[SESSION_COUNT_KEY] = session.note(payload)
    return payload


def session_print_count_value(prints_payload: Any) -> int:
    """Session count already stamped, else this payload's real tape rows."""
    if isinstance(prints_payload, Mapping) and SESSION_COUNT_KEY in prints_payload:
        raw = prints_payload.get(SESSION_COUNT_KEY)
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass
    return payload_print_count(prints_payload)


def watch_print_count_dashboard_line(prints_payload: Any) -> str:
    """One short header bit. Empty tape is 0, never synthetic rows."""
    return f"prints this session: {session_print_count_value(prints_payload)}"
