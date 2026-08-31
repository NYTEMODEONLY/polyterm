"""Honest wallet P&L from lagged Data API activity cashflow.

Do not report SUM(positions.cashPnl). That field drops redeemed winners
and can show a profitable wallet as a loss. Official lb-api /profit is a
pre-fee cross-check only (taker fees after Jun 2026). Do not trust makerPnl.

P&L = SELL + REDEEM + MERGE + REBATE - BUY - SPLIT + open-size mark
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple

import requests

from ..api.data_api import DataAPIClient
from ..api.data_api_lag import label_payload

SOURCE = "activity-cashflow"
VS_LEADERBOARD = "pre-fee"
LB_API_BASE = "https://lb-api.polymarket.com"
LB_API_PROFIT_PATH = "/profit"

ACTIVITY_PAGE_SIZE = 500
ACTIVITY_OFFSET_CAP = 5000
POSITIONS_PAGE_SIZE = 500
POSITIONS_OFFSET_CAP = 9500

# Signed cashflow types. TRADE is classified via side=BUY|SELL.
CASH_IN_TYPES = frozenset({"sell", "redeem", "merge", "rebate"})
CASH_OUT_TYPES = frozenset({"buy", "split"})
REBATE_TYPES = frozenset({"rebate", "maker_rebate", "taker_rebate"})
TRADE_TYPES = frozenset({"", "trade", "trade_matched"})

# Types we will not turn into cash even if usdcSize is present.
SKIP_TYPES = frozenset({
    "deposit",
    "withdrawal",
    "reward",
    "referral_reward",
    "conversion",
    "yield",
    "liquidity",
})


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def classify_activity_type(row: Any) -> Optional[str]:
    """Return a canonical cashflow type, or None to skip.

    Accepts Data API `type=TRADE` plus `side=BUY|SELL`, and the payload
    types BUY, SELL, REDEEM, MERGE, SPLIT, REBATE / MAKER_REBATE / TAKER_REBATE.
    Unknown types are not classified into cash.
    """
    if not isinstance(row, Mapping):
        return None

    raw = str(row.get("type") or "").strip().lower()
    side = str(row.get("side") or "").strip().lower()

    if raw in SKIP_TYPES:
        return None
    if raw in REBATE_TYPES:
        return "rebate"
    if raw in CASH_IN_TYPES or raw in CASH_OUT_TYPES:
        return raw
    if raw in TRADE_TYPES:
        if side in ("buy", "sell"):
            return side
        return None
    return None


def activity_usdc(row: Mapping[str, Any]) -> Optional[float]:
    """Cash amount from a real activity field. Does not invent size*price."""
    amount = _as_float(row.get("usdcSize"))
    if amount is None:
        amount = _as_float(row.get("usdc_size"))
    return amount


def activity_cash_delta(row: Any) -> Optional[Tuple[str, float]]:
    """Return (canonical_type, signed_usdc) or None when cash cannot be backed."""
    kind = classify_activity_type(row)
    if kind is None or not isinstance(row, Mapping):
        return None
    amount = activity_usdc(row)
    if amount is None:
        return None
    magnitude = abs(amount)
    if kind in CASH_OUT_TYPES:
        return kind, -magnitude
    if kind in CASH_IN_TYPES:
        return kind, magnitude
    return None


def replay_cashflow(activities: Iterable[Any]) -> Dict[str, Any]:
    """Replay BUY/SELL/REDEEM/MERGE/SPLIT/REBATE into signed cashflow.

    Unknown, malformed, or untyped rows are skipped. Cash is never invented.
    This does not read cashPnl or makerPnl.
    """
    totals = {
        "buy": 0.0,
        "sell": 0.0,
        "redeem": 0.0,
        "merge": 0.0,
        "split": 0.0,
        "rebate": 0.0,
    }
    counts = {key: 0 for key in totals}
    cashflow = 0.0
    included = 0
    skipped_unknown = 0
    skipped_malformed = 0
    unknown_types: List[str] = []

    rows = list(activities or [])
    for row in rows:
        if not isinstance(row, Mapping):
            skipped_malformed += 1
            continue
        kind = classify_activity_type(row)
        if kind is None:
            skipped_unknown += 1
            raw = str(row.get("type") or "").strip()
            if raw and raw not in unknown_types:
                unknown_types.append(raw)
            continue
        delta = activity_cash_delta(row)
        if delta is None:
            skipped_malformed += 1
            continue
        kind, signed = delta
        totals[kind] += abs(signed)
        counts[kind] += 1
        cashflow += signed
        included += 1

    return {
        "cashflow": cashflow,
        "totals": totals,
        "counts": counts,
        "included": included,
        "skipped_unknown": skipped_unknown,
        "skipped_malformed": skipped_malformed,
        "unknown_types": unknown_types,
        "activity_count": len(rows),
    }


def position_mark(position: Any) -> Optional[float]:
    """Mark remaining size from currentValue or size*curPrice. Not cashPnl."""
    if not isinstance(position, Mapping):
        return None
    size = _as_float(position.get("size"))
    if size is None or size <= 0:
        return None
    current = _as_float(position.get("currentValue"))
    if current is None:
        current = _as_float(position.get("current_value"))
    if current is not None:
        return current
    price = _as_float(position.get("curPrice"))
    if price is None:
        price = _as_float(position.get("cur_price"))
    if price is None:
        return None
    return size * price


def mark_open_positions(positions: Iterable[Any]) -> Dict[str, Any]:
    """Sum an open-size mark from Data API positions when fields exist."""
    open_mark = 0.0
    open_count = 0
    skipped = 0
    rows = list(positions or [])
    for position in rows:
        mark = position_mark(position)
        if mark is None:
            if isinstance(position, Mapping):
                skipped += 1
            continue
        open_mark += mark
        open_count += 1
    return {
        "open_mark": open_mark,
        "open_positions": open_count,
        "positions_count": len(rows),
        "skipped_unmarked": skipped,
    }


def parse_leaderboard_profit(payload: Any) -> Optional[float]:
    """Read lb-api /profit amount. Never uses makerPnl as the value."""
    if payload is None:
        return None
    row: Any = payload
    if isinstance(payload, list):
        if not payload:
            return None
        row = payload[0]
    elif isinstance(payload, Mapping):
        nested = payload.get("data", payload.get("profit"))
        if isinstance(nested, list):
            if not nested:
                return None
            row = nested[0]
        elif nested is not None and not isinstance(nested, Mapping):
            row = nested
        elif isinstance(nested, Mapping):
            row = nested
    if isinstance(row, Mapping):
        return _as_float(row.get("amount", row.get("profit", row.get("pnl"))))
    return _as_float(row)


def _unwrap_list(payload: Any, *keys: str) -> List[Any]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        for key in keys:
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
    raise TypeError("Data API did not return a list")


def build_report(
    address: str,
    cashflow_result: Mapping[str, Any],
    mark_result: Optional[Mapping[str, Any]] = None,
    leaderboard_profit: Optional[float] = None,
    quality_flags: Optional[Iterable[str]] = None,
    empty: bool = False,
) -> Dict[str, Any]:
    """Assemble the labeled P&L payload. Source of truth is activity cashflow."""
    flags: List[str] = list(quality_flags or [])
    cashflow = cashflow_result.get("cashflow")
    open_mark = None
    open_positions = 0
    if mark_result is not None:
        open_mark = mark_result.get("open_mark")
        open_positions = int(mark_result.get("open_positions") or 0)

    pnl = None
    if not empty and cashflow is not None and open_mark is not None:
        pnl = float(cashflow) + float(open_mark)
    elif not empty and cashflow is not None and mark_result is None:
        pnl = None

    if empty:
        cashflow = None
        pnl = None
        if "empty_activity" not in flags:
            flags.append("empty_activity")

    payload = {
        "address": address,
        "source": SOURCE,
        "vs_leaderboard": VS_LEADERBOARD,
        "vs-leaderboard": VS_LEADERBOARD,
        "pnl": pnl,
        "cashflow": None if empty else cashflow,
        "open_mark": open_mark,
        "open_positions": open_positions,
        "leaderboard_profit": leaderboard_profit,
        "activity_count": cashflow_result.get("activity_count", 0),
        "included_counts": dict(cashflow_result.get("counts") or {}),
        "totals": dict(cashflow_result.get("totals") or {}),
        "skipped_unknown": cashflow_result.get("skipped_unknown", 0),
        "skipped_malformed": cashflow_result.get("skipped_malformed", 0),
        "unknown_types": list(cashflow_result.get("unknown_types") or []),
        "empty": empty,
        "quality_flags": flags,
    }
    return label_payload(payload, quality_flags=flags)


def fetch_leaderboard_profit(
    address: str,
    http=None,
    base_url: str = LB_API_BASE,
    timeout: int = 15,
) -> Optional[float]:
    """Optional lb-api /profit cross-check. Pre-fee after Jun 2026 taker fees.

    Missing or error returns None. Callers must not invent a fee gap.
    """
    session = http or requests
    url = f"{base_url.rstrip('/')}{LB_API_PROFIT_PATH}"
    response = session.get(
        url,
        params={"window": "all", "address": address},
        timeout=timeout,
    )
    response.raise_for_status()
    return parse_leaderboard_profit(response.json())


class CashflowPnl:
    """Fetch lagged Data API activity/positions and compute cashflow P&L."""

    def __init__(self, data_api=None, http=None, lb_api_base: str = LB_API_BASE):
        self.data_api = data_api or DataAPIClient()
        self.http = http
        self.lb_api_base = lb_api_base

    def compute(self, address: str) -> Dict[str, Any]:
        """Return labeled wallet P&L. Activity fetch errors raise.

        Empty activity is an honest empty payload, not a synthetic P&L.
        Leaderboard and open-mark failures become null plus quality flags.
        """
        activities, activity_truncated = self._fetch_activity(address)
        flags: List[str] = []
        if activity_truncated:
            flags.append("activity_truncated")

        cashflow_result = replay_cashflow(activities)
        empty = cashflow_result["included"] == 0 and cashflow_result["activity_count"] == 0

        mark_result: Optional[Dict[str, Any]] = None
        try:
            positions, positions_truncated = self._fetch_positions(address)
            mark_result = mark_open_positions(positions)
            if positions_truncated:
                flags.append("positions_truncated")
            if mark_result.get("skipped_unmarked"):
                flags.append("some_positions_unmarked")
        except Exception:
            flags.append("open_mark_unavailable")
            mark_result = None

        leaderboard_profit = None
        try:
            leaderboard_profit = fetch_leaderboard_profit(
                address,
                http=self.http,
                base_url=self.lb_api_base,
            )
            if leaderboard_profit is None:
                flags.append("leaderboard_profit_unavailable")
        except Exception:
            leaderboard_profit = None
            flags.append("leaderboard_profit_unavailable")

        if cashflow_result["skipped_unknown"]:
            flags.append("skipped_unknown_activity_types")
        if cashflow_result["skipped_malformed"]:
            flags.append("skipped_malformed_activity")
        if empty and mark_result and mark_result.get("open_positions"):
            flags.append("activity_empty_with_open_positions")

        return build_report(
            address=address,
            cashflow_result=cashflow_result,
            mark_result=mark_result,
            leaderboard_profit=leaderboard_profit,
            quality_flags=flags,
            empty=empty,
        )

    def _fetch_activity(self, address: str) -> Tuple[List[Any], bool]:
        return self._paginate(
            lambda limit, offset: self.data_api.get_activity(
                address,
                limit=limit,
                offset=offset,
                sort_direction="ASC",
            ),
            unwrap_keys=("data", "activity"),
            page_size=ACTIVITY_PAGE_SIZE,
            max_offset=ACTIVITY_OFFSET_CAP,
        )

    def _fetch_positions(self, address: str) -> Tuple[List[Any], bool]:
        return self._paginate(
            lambda limit, offset: self.data_api.get_positions(
                address,
                limit=limit,
                offset=offset,
                size_threshold=0,
            ),
            unwrap_keys=("data", "positions"),
            page_size=POSITIONS_PAGE_SIZE,
            max_offset=POSITIONS_OFFSET_CAP,
        )

    def _paginate(
        self,
        fetch_page,
        unwrap_keys: Tuple[str, ...],
        page_size: int,
        max_offset: int,
    ) -> Tuple[List[Any], bool]:
        rows: List[Any] = []
        offset = 0
        truncated = False
        while offset <= max_offset:
            try:
                payload = fetch_page(page_size, offset)
            except Exception:
                if offset == 0:
                    raise
                truncated = True
                break
            page = _unwrap_list(payload, *unwrap_keys)
            rows.extend(page)
            if len(page) < page_size:
                break
            offset += len(page)
            if offset > max_offset:
                truncated = True
                break
        return rows, truncated
