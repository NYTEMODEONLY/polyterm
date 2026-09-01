"""Wallet-level whale view from lagged Data API prints.

This is print_scanner output, grouped by wallet when addresses exist.
It is not insider scoring, syndicate detection, or copy-trade execution.
Empty tape stays empty. Wallets are not invented.
"""

from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from ..api.data_api_lag import label_payload
from .print_scanner import PrintScanner, match_prints


# Same floor as polyterm watch / alerts print rules.
DEFAULT_PRINT_MIN_NOTIONAL = 10000.0


def scan_whale_prints(
    scanner: Optional[PrintScanner] = None,
    min_notional: float = DEFAULT_PRINT_MIN_NOTIONAL,
    market: Optional[str] = None,
    hours: Optional[int] = None,
    limit: int = 20,
    now: Optional[datetime] = None,
) -> Dict[str, Any]:
    """Return lagged Data API prints and a wallet rollup of that tape.

    Uses PrintScanner. Does not call CLOB. Does not synthesize wallets when
    the Data API page is empty or no row meets min_notional.
    """
    scanner = scanner or PrintScanner()
    cap = max(int(limit or 20), 1)
    fetch_limit = max(cap * 5, 100)
    fetched = scanner.fetch_prints(
        min_notional=min_notional,
        market=market,
        limit=fetch_limit,
    )
    matched = match_prints(
        fetched.get("prints") or [],
        min_notional=min_notional,
        market=market,
    )
    quality_flags = list(fetched.get("quality_flags") or [])

    dropped_old = 0
    if hours is not None:
        matched, dropped_old = _filter_hours(matched, hours=hours, now=now)
        if dropped_old:
            quality_flags.append("dropped_prints_outside_hours")

    if not matched and int(fetched.get("fetched") or 0) > 0:
        quality_flags.append("no_prints_at_min_notional")

    displayed = matched[:cap]
    wallets = rollup_prints_by_wallet(displayed)

    return label_payload({
        "mode": "wallet_trades",
        "min_notional": min_notional,
        "market": market,
        "hours": hours,
        "fetched": fetched.get("fetched", 0),
        "skipped": fetched.get("skipped", 0),
        "matched": len(matched),
        "count": len(displayed),
        "prints": displayed,
        "wallets": wallets,
        "wallet_count": len(wallets),
        "quality_flags": quality_flags,
    })


def rollup_prints_by_wallet(prints: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Aggregate real prints by wallet. Missing wallets are omitted, not invented."""
    by_wallet: Dict[str, Dict[str, Any]] = {}
    for row in prints or []:
        if not isinstance(row, Mapping):
            continue
        address = row.get("wallet")
        if not address:
            continue
        address = str(address)
        item = by_wallet.setdefault(
            address,
            {
                "address": address,
                "trade_count": 0,
                "notional": 0.0,
                "largest_trade": 0.0,
                "markets": Counter(),
                "trades": [],
            },
        )
        notional = _optional_float(row.get("notional")) or 0.0
        item["trade_count"] += 1
        item["notional"] += notional
        item["largest_trade"] = max(item["largest_trade"], notional)
        market_label = _market_label(row)
        if market_label:
            item["markets"][market_label] += 1
        item["trades"].append(dict(row))

    wallets = []
    for item in by_wallet.values():
        item["top_markets"] = item["markets"].most_common(5)
        item.pop("markets", None)
        wallets.append(item)
    wallets.sort(key=lambda row: row["notional"], reverse=True)
    return wallets


def _filter_hours(
    prints: Sequence[Mapping[str, Any]],
    hours: int,
    now: Optional[datetime] = None,
) -> Tuple[List[Mapping[str, Any]], int]:
    """Drop prints older than the window. Unknown timestamps are kept, not invented."""
    try:
        window = float(hours)
    except (TypeError, ValueError):
        return list(prints or []), 0
    if window <= 0:
        return list(prints or []), 0

    now_dt = now or datetime.now(timezone.utc)
    if now_dt.tzinfo is None:
        now_dt = now_dt.replace(tzinfo=timezone.utc)
    cutoff = now_dt - timedelta(hours=window)

    kept: List[Mapping[str, Any]] = []
    dropped = 0
    for row in prints or []:
        parsed = _print_datetime(row)
        if parsed is not None and parsed < cutoff:
            dropped += 1
            continue
        kept.append(row)
    return kept, dropped


def _print_datetime(row: Mapping[str, Any]) -> Optional[datetime]:
    iso = row.get("timestamp_iso")
    if iso:
        try:
            parsed = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            pass
    timestamp = row.get("timestamp")
    if isinstance(timestamp, datetime):
        parsed = timestamp
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    if isinstance(timestamp, (int, float)) and timestamp:
        try:
            return datetime.fromtimestamp(float(timestamp), timezone.utc)
        except (OSError, OverflowError, ValueError):
            return None
    return None


def _market_label(row: Mapping[str, Any]) -> Optional[str]:
    for key in ("market_slug", "market_id", "condition_id", "market_title", "event_slug"):
        value = row.get(key)
        if value:
            text = str(value).strip()
            if text:
                return text
    return None


def _optional_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
