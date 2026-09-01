"""Detect a connected CLOB WebSocket that is not actually ticking.

CLOB market sockets can stay up on protocol PING/PONG (or other non-book
frames) while ``book`` / ``price_change`` events never arrive. A still book
is not live. This module does not open sockets; it only classifies ticks
and freshness from timestamps the caller already observed.
"""

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping, Optional

BOOK_TICK_TYPES = frozenset({"book", "price_change", "last_trade_price"})
DEFAULT_STALE_AFTER_SECONDS = 20.0
WS_STALE_FLAG = "ws_stale"
WS_STALE_BANNER = "WS connected, no book ticks"
CLOB_WS_SOURCE = "clob_ws"
CLOB_REST_SOURCE = "clob_rest"
NO_BOOK_SOURCE = "none"


def book_tick_type(message: Any) -> Optional[str]:
    """Return the book-tick type, or None when the frame is not a book tick."""
    if not isinstance(message, Mapping):
        return None
    msg_type = str(message.get("type") or message.get("event_type") or "").strip()
    if msg_type in BOOK_TICK_TYPES:
        return msg_type
    return None


def is_book_tick(message: Any) -> bool:
    """True for ``book``, ``price_change``, or ``last_trade_price`` frames."""
    return book_tick_type(message) is not None


def _now(now: Optional[datetime] = None) -> datetime:
    if now is not None:
        if now.tzinfo is None:
            return now.replace(tzinfo=timezone.utc)
        return now
    return datetime.now(timezone.utc)


def _aware(value: Optional[datetime]) -> Optional[datetime]:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def tick_age_seconds(
    last_tick_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> Optional[float]:
    """Seconds since the last book tick. None when no tick has been seen."""
    stamp = _aware(last_tick_at)
    if stamp is None:
        return None
    return max(0.0, (_now(now) - stamp).total_seconds())


@dataclass
class BookFreshness:
    """Honesty report for the book watch is displaying."""

    source: str
    ws_connected: bool
    ws_stale: bool
    live: bool
    stale_after_seconds: float
    last_tick_age_seconds: Optional[float] = None
    last_tick_type: Optional[str] = None
    banner: Optional[str] = None
    quality_flags: List[str] = field(default_factory=list)
    token_id: Optional[str] = None
    best_bid: Optional[float] = None
    best_ask: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "source": self.source,
            "ws_connected": self.ws_connected,
            "ws_stale": self.ws_stale,
            "live": self.live,
            "stale_after_seconds": self.stale_after_seconds,
            "quality_flags": list(self.quality_flags),
        }
        if self.last_tick_age_seconds is not None:
            payload["last_tick_age_seconds"] = self.last_tick_age_seconds
        if self.last_tick_type:
            payload["last_tick_type"] = self.last_tick_type
        if self.banner:
            payload["banner"] = self.banner
        if self.token_id:
            payload["token_id"] = self.token_id
        if self.best_bid is not None:
            payload["best_bid"] = self.best_bid
        if self.best_ask is not None:
            payload["best_ask"] = self.best_ask
        return payload


class BookTickTracker:
    """Thread-safe last-tick clock for a CLOB market socket."""

    def __init__(self, stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS):
        self.stale_after_seconds = float(stale_after_seconds)
        self._lock = threading.Lock()
        self.ws_connected = False
        self.connected_at: Optional[datetime] = None
        self.last_tick_at: Optional[datetime] = None
        self.last_tick_type: Optional[str] = None
        self.tick_count = 0

    def mark_connected(self, connected: bool, at: Optional[datetime] = None) -> None:
        """Record whether the socket currently looks connected."""
        stamp = _now(at)
        with self._lock:
            self.ws_connected = bool(connected)
            if connected:
                if self.connected_at is None:
                    self.connected_at = stamp
            else:
                self.connected_at = None

    def note_message(self, message: Any, at: Optional[datetime] = None) -> bool:
        """Record a book tick. Non-book frames (PING, tick_size_change) return False."""
        tick_type = book_tick_type(message)
        if tick_type is None:
            return False
        stamp = _now(at)
        with self._lock:
            self.last_tick_at = stamp
            self.last_tick_type = tick_type
            self.tick_count += 1
            self.ws_connected = True
            if self.connected_at is None:
                self.connected_at = stamp
        return True

    def assess(
        self,
        now: Optional[datetime] = None,
        rest_fallback: bool = False,
        has_rest_book: bool = False,
        token_id: Optional[str] = None,
        best_bid: Optional[float] = None,
        best_ask: Optional[float] = None,
    ) -> BookFreshness:
        """Classify the current book as live WS, stale WS, or REST snapshot."""
        return assess_book_freshness(
            ws_connected=self.ws_connected,
            last_tick_at=self.last_tick_at,
            connected_at=self.connected_at,
            last_tick_type=self.last_tick_type,
            now=now,
            stale_after_seconds=self.stale_after_seconds,
            rest_fallback=rest_fallback,
            has_rest_book=has_rest_book,
            token_id=token_id,
            best_bid=best_bid,
            best_ask=best_ask,
        )


def assess_book_freshness(
    *,
    ws_connected: bool,
    last_tick_at: Optional[datetime] = None,
    connected_at: Optional[datetime] = None,
    last_tick_type: Optional[str] = None,
    now: Optional[datetime] = None,
    stale_after_seconds: float = DEFAULT_STALE_AFTER_SECONDS,
    rest_fallback: bool = False,
    has_rest_book: bool = False,
    token_id: Optional[str] = None,
    best_bid: Optional[float] = None,
    best_ask: Optional[float] = None,
) -> BookFreshness:
    """Return a labeled freshness report. Never calls a still book live.

    A socket that has been connected for ``stale_after_seconds`` without a
    ``book`` / ``price_change`` / ``last_trade_price`` tick is ``ws_stale``.
    REST snapshots are labeled ``clob_rest`` and ``live=false``.
    """
    stale_after = float(stale_after_seconds)
    if stale_after <= 0:
        stale_after = DEFAULT_STALE_AFTER_SECONDS

    age = tick_age_seconds(last_tick_at, now)
    connected_age = tick_age_seconds(connected_at, now) if ws_connected else None
    rest_ok = bool(rest_fallback and has_rest_book)

    flags: List[str] = []
    ws_stale = False
    live = False
    source = NO_BOOK_SOURCE
    banner = None

    if ws_connected and age is not None and age < stale_after:
        live = True
        source = CLOB_WS_SOURCE
        flags.append(CLOB_WS_SOURCE)
    elif ws_connected:
        waited = age if age is not None else connected_age
        if waited is None or waited >= stale_after:
            ws_stale = True
            banner = WS_STALE_BANNER
            flags.append(WS_STALE_FLAG)
            if rest_ok:
                source = CLOB_REST_SOURCE
                flags.append(CLOB_REST_SOURCE)
            else:
                source = NO_BOOK_SOURCE
        else:
            if rest_ok:
                source = CLOB_REST_SOURCE
                flags.append(CLOB_REST_SOURCE)
    elif rest_ok:
        source = CLOB_REST_SOURCE
        flags.append(CLOB_REST_SOURCE)
    else:
        source = NO_BOOK_SOURCE

    return BookFreshness(
        source=source,
        ws_connected=bool(ws_connected),
        ws_stale=ws_stale,
        live=live,
        stale_after_seconds=stale_after,
        last_tick_age_seconds=age,
        last_tick_type=last_tick_type,
        banner=banner,
        quality_flags=flags,
        token_id=token_id,
        best_bid=best_bid,
        best_ask=best_ask,
    )
