"""One watch-loop helper: lagged prints, CLOB book snapshot, notify events.

Watch remains a single process. This module does not spawn a watchdog
command. Prints are lagged Data API fills. A connected WebSocket without
book ticks is not live.
"""

import asyncio
import threading
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

from ..api.data_api_lag import label_payload
from ..api.market_utils import get_clob_token_ids, get_market_condition_id, get_primary_clob_token_id
from .print_scanner import PrintScanner, match_prints, print_message
from .uma_tracker import snapshot_market_resolution
from .ws_book_freshness import (
    CLOB_REST_SOURCE,
    DEFAULT_STALE_AFTER_SECONDS,
    BookTickTracker,
    assess_book_freshness,
    is_book_tick,
)

DEFAULT_PRINT_MIN_NOTIONAL = 10000.0
DEFAULT_PRINT_LIMIT = 8
NOTIFY_CHANNELS = frozenset({"telegram", "discord"})


def empty_prints_payload(extra_flags: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    """Labeled empty tape. Never a synthetic fill."""
    flags = ["empty_data_api_page"]
    if extra_flags:
        flags.extend(extra_flags)
    return label_payload({
        "prints": [],
        "count": 0,
        "fetched": 0,
        "skipped": 0,
        "matched": 0,
        "quality_flags": flags,
    })


def watch_print_market_id(market_data: Optional[Mapping[str, Any]], market_query: str) -> Optional[str]:
    """Prefer a CLOB condition ID, then slug, then the trader's query string."""
    if isinstance(market_data, dict):
        condition_id = get_market_condition_id(market_data)
        if condition_id:
            return condition_id
        slug = market_data.get("slug") or market_data.get("market_slug")
        if slug:
            return str(slug).strip() or None
        gamma_id = market_data.get("id")
        if gamma_id:
            return str(gamma_id).strip() or None
    query = str(market_query or "").strip()
    return query or None


def resolve_watch_market_data(gamma_client: Any, market: str) -> Optional[Dict[str, Any]]:
    """Resolve Gamma market metadata without prompting. Failures return None."""
    if gamma_client is None:
        return None
    try:
        data = gamma_client.get_market(market)
        if isinstance(data, dict) and (data.get("id") or data.get("conditionId") or data.get("slug")):
            return data
    except Exception:
        pass
    try:
        results = gamma_client.search_markets(market, limit=5)
    except Exception:
        return None
    if isinstance(results, list):
        for item in results:
            if isinstance(item, dict) and (item.get("id") or item.get("conditionId") or item.get("slug")):
                return item
    return None


def fetch_watch_prints(
    print_scanner: Optional[PrintScanner],
    market_data: Optional[Mapping[str, Any]],
    market_query: str,
    limit: int = DEFAULT_PRINT_LIMIT,
) -> Dict[str, Any]:
    """Pull lagged Data API prints for the resolved market. Empty tape stays empty."""
    if print_scanner is None:
        return empty_prints_payload(["prints_unavailable"])

    ident = watch_print_market_id(market_data, market_query)
    if not ident:
        return empty_prints_payload()

    try:
        payload = print_scanner.fetch_prints(market=ident, limit=max(int(limit or 8), 1))
    except Exception as exc:
        empty = empty_prints_payload(["prints_unavailable"])
        empty["prints_error"] = str(exc)
        return empty

    if not isinstance(payload, dict):
        return empty_prints_payload(["prints_unavailable"])

    prints = [row for row in (payload.get("prints") or []) if isinstance(row, dict)]
    flags = list(payload.get("quality_flags") or [])
    labeled = label_payload({
        "market": ident,
        "fetched": payload.get("fetched", len(prints)),
        "skipped": payload.get("skipped", 0),
        "count": len(prints),
        "prints": prints,
        "quality_flags": flags,
    })
    return labeled


def matching_print_rows(
    prints_payload: Mapping[str, Any],
    min_notional: float,
) -> List[Dict[str, Any]]:
    """Prints that meet the watch min-notional. Unknown notional cannot match."""
    rows = prints_payload.get("prints") if isinstance(prints_payload, Mapping) else None
    return match_prints(rows or [], min_notional=min_notional)


def _level_price(level: Any) -> Optional[float]:
    if isinstance(level, Mapping):
        value = level.get("price")
    elif isinstance(level, (list, tuple)) and level:
        value = level[0]
    else:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def rest_top_of_book(book: Any) -> Dict[str, Optional[float]]:
    """Best bid/ask from a CLOB REST book dict. Missing sides stay None."""
    if not isinstance(book, dict):
        return {"best_bid": None, "best_ask": None}
    bids = book.get("bids") or []
    asks = book.get("asks") or []
    return {
        "best_bid": _level_price(bids[0]) if bids else None,
        "best_ask": _level_price(asks[0]) if asks else None,
    }


def fetch_rest_book(clob_client: Any, token_id: str, depth: int = 5) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """Fetch a CLOB REST book. Errors return (None, message), never a fake book."""
    if clob_client is None or not token_id:
        return None, None
    try:
        book = clob_client.get_order_book(token_id, depth=depth)
    except Exception as exc:
        return None, str(exc)
    if not isinstance(book, dict):
        return None, "CLOB REST book was not an object"
    return book, None


def build_book_payload(
    *,
    tracker: Optional[BookTickTracker] = None,
    rest_book: Optional[Dict[str, Any]] = None,
    token_id: Optional[str] = None,
    rest_error: Optional[str] = None,
    now: Optional[datetime] = None,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    ws_book: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Label WS vs REST book. REST is a snapshot, never live."""
    top = rest_top_of_book(ws_book if isinstance(ws_book, dict) else rest_book)
    has_rest = isinstance(rest_book, dict) and bool(rest_book.get("bids") or rest_book.get("asks"))
    has_ws_book = isinstance(ws_book, dict) and bool(ws_book.get("bids") or ws_book.get("asks"))
    if tracker is not None:
        freshness = tracker.assess(
            now=now,
            rest_fallback=True,
            has_rest_book=has_rest or has_ws_book,
            token_id=token_id,
            best_bid=top["best_bid"],
            best_ask=top["best_ask"],
        )
    else:
        freshness = assess_book_freshness(
            ws_connected=False,
            now=now,
            stale_after_seconds=stale_after_seconds,
            rest_fallback=True,
            has_rest_book=has_rest,
            token_id=token_id,
            best_bid=top["best_bid"],
            best_ask=top["best_ask"],
        )
    payload = freshness.to_dict()
    if rest_error:
        payload["rest_error"] = rest_error
        flags = list(payload.get("quality_flags") or [])
        if "clob_rest_unavailable" not in flags:
            flags.append("clob_rest_unavailable")
        payload["quality_flags"] = flags
    if freshness.ws_stale and freshness.source == CLOB_REST_SOURCE:
        payload["fallback"] = CLOB_REST_SOURCE
    return payload


class WatchBookSession:
    """Background CLOB WS for watch, with REST fallback when ticks freeze."""

    def __init__(
        self,
        clob_client: Any,
        token_ids: Sequence[str],
        stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    ):
        self.clob_client = clob_client
        self.token_ids = [str(tid) for tid in token_ids if tid]
        self.stale_after_seconds = float(stale_after_seconds)
        self.tracker = BookTickTracker(self.stale_after_seconds)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._last_ws_book: Optional[Dict[str, Any]] = None

    def start(self) -> None:
        """Start the WS listener thread. No-op when there are no token IDs."""
        if not self.token_ids or self.clob_client is None:
            return
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run_ws_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        self.tracker.mark_connected(False)

    def note_ws_message(self, data: Any, at: Optional[datetime] = None) -> None:
        """Record a WS frame. Used by the listener and by tests."""
        if not isinstance(data, dict):
            return
        self.tracker.note_message(data, at=at)
        if is_book_tick(data) and (data.get("bids") or data.get("asks")):
            with self._lock:
                self._last_ws_book = data

    def snapshot(self, now: Optional[datetime] = None) -> Dict[str, Any]:
        """Current book view: live WS ticks, or labeled REST fallback."""
        token_id = self.token_ids[0] if self.token_ids else None
        with self._lock:
            ws_book = dict(self._last_ws_book) if isinstance(self._last_ws_book, dict) else None
        rest_book = None
        rest_error = None
        freshness = self.tracker.assess(now=now, rest_fallback=False, has_rest_book=False)
        if not freshness.live:
            rest_book, rest_error = fetch_rest_book(self.clob_client, token_id or "")
        return build_book_payload(
            tracker=self.tracker,
            rest_book=rest_book,
            token_id=token_id,
            rest_error=rest_error,
            now=now,
            stale_after_seconds=self.stale_after_seconds,
            ws_book=ws_book if freshness.live else None,
        )

    def _run_ws_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def _listen():
            try:
                await self.clob_client.subscribe_orderbook(self.token_ids, self.note_ws_message)
                self.tracker.mark_connected(True)
                await self.clob_client.listen_orderbook(
                    max_reconnects=10,
                    message_timeout=max(self.stale_after_seconds * 3, 60.0),
                )
            except Exception:
                self.tracker.mark_connected(False)

        task = loop.create_task(_listen())

        async def _wait_for_stop():
            while not self._stop.is_set():
                await asyncio.sleep(0.25)
            task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
            closer = getattr(self.clob_client, "close_websocket", None)
            if closer is not None:
                try:
                    result = closer()
                    if hasattr(result, "__await__"):
                        await result
                except Exception:
                    pass

        try:
            loop.run_until_complete(_wait_for_stop())
        except Exception:
            self.tracker.mark_connected(False)
        finally:
            loop.close()


def collect_watch_surfaces(
    *,
    market: str,
    gamma_client: Any = None,
    clob_client: Any = None,
    print_scanner: Optional[PrintScanner] = None,
    market_data: Optional[Mapping[str, Any]] = None,
    book_session: Optional[WatchBookSession] = None,
    min_notional: float = DEFAULT_PRINT_MIN_NOTIONAL,
    print_limit: int = DEFAULT_PRINT_LIMIT,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Fetch prints + book + UMA/resolution for one watch scan. Does not invent tape or ticks."""
    resolved = market_data if isinstance(market_data, dict) else None
    if resolved is None:
        resolved = resolve_watch_market_data(gamma_client, market)

    prints_payload = fetch_watch_prints(
        print_scanner,
        resolved,
        market,
        limit=print_limit,
    )
    matched = matching_print_rows(prints_payload, min_notional)
    prints_payload = dict(prints_payload)
    prints_payload["min_notional"] = min_notional
    prints_payload["matched"] = len(matched)
    prints_payload["matched_prints"] = matched

    if book_session is not None:
        book_payload = book_session.snapshot(now=now)
    else:
        token_id = get_primary_clob_token_id(resolved) if resolved else None
        rest_book, rest_error = fetch_rest_book(clob_client, token_id or "")
        book_payload = build_book_payload(
            tracker=None,
            rest_book=rest_book,
            token_id=token_id,
            rest_error=rest_error,
            now=now,
            stale_after_seconds=stale_after_seconds,
        )

    resolution_market = resolved
    if isinstance(market_data, dict) and gamma_client is not None:
        fresh = resolve_watch_market_data(gamma_client, market)
        if isinstance(fresh, dict):
            resolution_market = fresh
    resolution_payload = snapshot_market_resolution(resolution_market, now=now)

    return {
        "prints": prints_payload,
        "book": book_payload,
        "resolution": resolution_payload,
    }


def print_event_id(print_row: Mapping[str, Any]) -> str:
    """Stable id for notify dedupe. Prefers transaction hash when present."""
    tx_hash = print_row.get("transaction_hash")
    if tx_hash:
        return "tx:{}".format(tx_hash)
    parts = [
        str(print_row.get("timestamp") or ""),
        str(print_row.get("wallet") or ""),
        str(print_row.get("notional") or ""),
        str(print_row.get("side") or ""),
        str(print_row.get("condition_id") or print_row.get("market_id") or ""),
    ]
    return "row:" + "|".join(parts)


def new_notify_state() -> Dict[str, Set[str]]:
    return {"print_ids": set(), "shift_ids": set()}


def notify_events_from_scan(
    prints_payload: Mapping[str, Any],
    shifts: Optional[Sequence[Mapping[str, Any]]],
    min_notional: float,
    state: Optional[Dict[str, Set[str]]] = None,
) -> List[Dict[str, Any]]:
    """Events worth a Telegram/Discord send. Empty poll returns []."""
    state = state if state is not None else new_notify_state()
    events: List[Dict[str, Any]] = []

    for row in matching_print_rows(prints_payload, min_notional):
        event_id = print_event_id(row)
        if event_id in state["print_ids"]:
            continue
        state["print_ids"].add(event_id)
        events.append({
            "kind": "print",
            "id": event_id,
            "title": "Lagged Data API print",
            "message": print_message(row, min_notional=min_notional),
            "level": "warning",
            "data": dict(row),
        })

    for shift in shifts or []:
        if not isinstance(shift, Mapping):
            continue
        types = shift.get("shift_type") or []
        if not types:
            continue
        market_id = str(shift.get("market_id") or shift.get("title") or "")
        type_key = ",".join(str(item) for item in types)
        event_id = "shift:{}:{}".format(market_id, type_key)
        if event_id in state["shift_ids"]:
            continue
        state["shift_ids"].add(event_id)
        title = str(shift.get("title") or market_id or "Market shift")
        events.append({
            "kind": "threshold",
            "id": event_id,
            "title": title,
            "message": "Threshold event: {}".format(type_key),
            "level": "warning",
            "data": {
                "market_id": market_id,
                "shift_type": list(types),
            },
        })
    return events


def watch_notifier(config: Any, channel: Optional[str]):
    """NotificationManager for one requested channel, or None."""
    if not channel or str(channel).strip().lower() not in NOTIFY_CHANNELS:
        return None
    from .notifications import NotificationConfig, NotificationManager

    raw = {}
    getter = getattr(config, "notification_config", None)
    if callable(getter):
        raw = getter() or {}
    elif isinstance(getter, dict):
        raw = getter
    elif config is not None:
        raw = getattr(config, "notification_config", {}) or {}
    if not isinstance(raw, dict):
        raw = {}

    notif = NotificationConfig.from_dict(raw)
    requested = str(channel).strip().lower()
    notif.telegram_enabled = requested == "telegram"
    notif.discord_enabled = requested == "discord"
    notif.system_enabled = False
    notif.sound_enabled = False
    notif.email_enabled = False
    return NotificationManager(notif)


def dispatch_watch_notifications(
    channel: Optional[str],
    events: Sequence[Mapping[str, Any]],
    manager: Any,
) -> List[Dict[str, Any]]:
    """Send notify-worthy events. Does not send on an empty poll."""
    if not events or manager is None:
        return []
    requested = str(channel or "").strip().lower()
    if requested not in NOTIFY_CHANNELS:
        return []
    sent: List[Dict[str, Any]] = []
    for event in events:
        result = manager.send(
            title=str(event.get("title") or "PolyTerm watch"),
            message=str(event.get("message") or ""),
            level=str(event.get("level") or "info"),
            data=event.get("data") if isinstance(event.get("data"), dict) else None,
        )
        channel_ok = False
        if isinstance(result, dict):
            channel_ok = bool(result.get(requested))
        sent.append({
            "kind": event.get("kind"),
            "id": event.get("id"),
            "channel": requested,
            "sent": channel_ok,
        })
    return sent


def token_ids_for_market(market_data: Optional[Mapping[str, Any]]) -> List[str]:
    if not isinstance(market_data, dict):
        return []
    return get_clob_token_ids(market_data)
