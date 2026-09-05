"""Lagged Data API position for the wallet already on this watch session.

Watch stays one process. This is not a new screen and not a second wallet
client. No wallet configured means omit the line entirely. Empty Data API
rows are "no position", never fake zero shares or P&L. P&L is activity
cashflow plus open-size mark, not SUM(cashPnl).
"""

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set

from ..api.data_api_lag import label_payload
from ..api.market_utils import get_clob_token_ids, get_market_condition_id
from .pnl_cashflow import mark_open_positions, replay_cashflow

POSITION_PAGE_SIZE = 100
ACTIVITY_PAGE_SIZE = 500
ACTIVITY_OFFSET_CAP = 1500
PNL_SOURCE = "activity-cashflow"


def configured_wallet_address(config: Any) -> Optional[str]:
    """Saved view-only wallet, or None. Empty / missing is not invented."""
    if config is None:
        return None
    candidates: List[Any] = []
    getter = getattr(config, "get", None)
    if callable(getter):
        try:
            candidates.append(getter("wallet.address", ""))
        except TypeError:
            try:
                candidates.append(getter("wallet.address"))
            except Exception:
                pass
        except Exception:
            pass
    candidates.append(getattr(config, "wallet_address", None))
    for raw in candidates:
        if isinstance(raw, str):
            address = raw.strip()
            if address:
                return address
    return None


def watch_position_identifiers(
    market_data: Optional[Mapping[str, Any]],
    market_query: str = "",
) -> List[str]:
    """IDs that can match a Data API position/activity row to this market."""
    idents: List[str] = []
    if isinstance(market_data, Mapping):
        condition_id = get_market_condition_id(market_data)
        if condition_id:
            idents.append(str(condition_id).strip())
        for key in ("slug", "market_slug", "eventSlug", "event_slug"):
            value = market_data.get(key)
            if value:
                idents.append(str(value).strip())
        gamma_id = market_data.get("id")
        if gamma_id:
            idents.append(str(gamma_id).strip())
        for token_id in get_clob_token_ids(market_data):
            if token_id:
                idents.append(str(token_id).strip())
    query = str(market_query or "").strip()
    if query:
        idents.append(query)
    seen = set()
    unique: List[str] = []
    for ident in idents:
        if ident and ident not in seen:
            unique.append(ident)
            seen.add(ident)
    return unique


def _condition_id_for_api(identifiers: Sequence[str]) -> Optional[str]:
    """Data API `market=` wants a CLOB condition ID, not a Gamma slug."""
    for ident in identifiers:
        if ident.startswith("0x") and len(ident) > 2:
            return ident
    return None


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _unwrap_rows(payload: Any, *keys: str) -> Optional[List[Any]]:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, Mapping):
        for key in keys:
            nested = payload.get(key)
            if isinstance(nested, list):
                return nested
    return None


def _row_tokens(row: Mapping[str, Any]) -> Set[str]:
    tokens: Set[str] = set()
    for key in (
        "conditionId",
        "condition_id",
        "market",
        "market_id",
        "slug",
        "market_slug",
        "eventSlug",
        "event_slug",
        "asset",
        "asset_id",
        "token_id",
        "tokenId",
    ):
        value = row.get(key)
        if value:
            tokens.add(str(value).strip())
    return {item for item in tokens if item}


def matching_market_rows(
    rows: Iterable[Any],
    identifiers: Sequence[str],
    api_filtered: bool = False,
) -> List[Dict[str, Any]]:
    """Keep rows that belong to this market. Unknown ids do not match."""
    wanted = {str(item).strip() for item in identifiers if item}
    matched: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, Mapping):
            continue
        tokens = _row_tokens(row)
        if tokens and wanted and tokens.isdisjoint(wanted):
            continue
        if not tokens and not api_filtered:
            continue
        matched.append(dict(row))
    return matched


def _position_legs(rows: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Open size/outcome legs. Missing size is skipped, never a fake 0."""
    legs: List[Dict[str, Any]] = []
    for row in rows:
        size = _as_float(row.get("size"))
        if size is None or size <= 0:
            continue
        leg: Dict[str, Any] = {"shares": size}
        outcome = row.get("outcome")
        if outcome is None or outcome == "":
            index = row.get("outcomeIndex", row.get("outcome_index"))
            if index is not None and index != "":
                outcome = index
        if outcome is not None and outcome != "":
            leg["outcome"] = str(outcome)
        asset = row.get("asset") or row.get("asset_id") or row.get("token_id")
        if asset:
            leg["asset"] = str(asset)
        legs.append(leg)
    return legs


def _unavailable_payload(wallet: str, error: str, extra_flags: Optional[Iterable[str]] = None) -> Dict[str, Any]:
    flags = ["position_unavailable"]
    if extra_flags:
        flags.extend(extra_flags)
    payload: Dict[str, Any] = {
        "wallet": wallet,
        "has_position": False,
        "position_error": str(error),
        "quality_flags": flags,
    }
    return label_payload(payload)


def _paginate_activity(data_api: Any, wallet: str, market: Optional[str]) -> tuple[List[Any], bool, Optional[str]]:
    rows: List[Any] = []
    truncated = False
    offset = 0
    while offset <= ACTIVITY_OFFSET_CAP:
        try:
            payload = data_api.get_activity(
                wallet,
                limit=ACTIVITY_PAGE_SIZE,
                offset=offset,
                sort_direction="ASC",
                market=market,
            )
        except Exception as exc:
            if offset == 0:
                return [], False, str(exc)
            truncated = True
            break
        page = _unwrap_rows(payload, "data", "activity")
        if page is None:
            if offset == 0:
                return [], False, "Data API activity was not a list"
            truncated = True
            break
        rows.extend(page)
        if len(page) < ACTIVITY_PAGE_SIZE:
            break
        offset += len(page)
        if offset > ACTIVITY_OFFSET_CAP:
            truncated = True
            break
    return rows, truncated, None


def fetch_watch_position(
    data_api: Any,
    wallet_address: Optional[str],
    market_data: Optional[Mapping[str, Any]] = None,
    market_query: str = "",
) -> Optional[Dict[str, Any]]:
    """Lagged position on the watched market, or None when no wallet.

    Network errors become a labeled unavailable object. They do not raise.
    """
    wallet = wallet_address.strip() if isinstance(wallet_address, str) else ""
    if not wallet:
        return None

    identifiers = watch_position_identifiers(market_data, market_query)
    if not identifiers:
        return _unavailable_payload(wallet, "watched market has no position identifier")

    if data_api is None:
        return _unavailable_payload(wallet, "data api client missing")

    market = _condition_id_for_api(identifiers)
    try:
        raw_positions = data_api.get_positions(
            wallet,
            limit=POSITION_PAGE_SIZE,
            size_threshold=0,
            market=market,
        )
    except Exception as exc:
        return _unavailable_payload(wallet, str(exc))

    position_rows = _unwrap_rows(raw_positions, "data", "positions")
    if position_rows is None:
        return _unavailable_payload(wallet, "Data API positions were not a list")

    matched = matching_market_rows(position_rows, identifiers, api_filtered=bool(market))
    legs = _position_legs(matched)
    flags: List[str] = []
    if len(position_rows) >= POSITION_PAGE_SIZE:
        flags.append("positions_truncated")

    payload: Dict[str, Any] = {
        "wallet": wallet,
        "has_position": bool(legs),
        "quality_flags": flags,
    }
    if market:
        payload["condition_id"] = market
    if legs:
        payload["legs"] = legs
        payload["shares"] = legs[0]["shares"]
        if "outcome" in legs[0]:
            payload["outcome"] = legs[0]["outcome"]
    else:
        flags.append("empty_position")
        payload["quality_flags"] = flags

    activity_rows, activity_truncated, activity_error = _paginate_activity(
        data_api, wallet, market
    )
    if activity_error:
        flags.append("cashflow_unavailable")
        payload["quality_flags"] = flags
        payload["cashflow_error"] = activity_error
        return label_payload(payload)

    matched_activity = matching_market_rows(
        activity_rows, identifiers, api_filtered=bool(market)
    )
    cashflow_result = replay_cashflow(matched_activity)
    mark_result = mark_open_positions(matched)
    if activity_truncated:
        flags.append("activity_truncated")
    if cashflow_result.get("skipped_unknown"):
        flags.append("skipped_unknown_activity_types")
    if cashflow_result.get("skipped_malformed"):
        flags.append("skipped_malformed_activity")

    if cashflow_result.get("included"):
        cashflow = cashflow_result.get("cashflow")
        payload["cashflow"] = cashflow
        payload["pnl_source"] = PNL_SOURCE
        open_mark = mark_result.get("open_mark")
        if open_mark is not None:
            payload["open_mark"] = open_mark
            if cashflow is not None:
                payload["pnl"] = float(cashflow) + float(open_mark)
    payload["quality_flags"] = flags
    return label_payload(payload)


def _fmt_shares(value: Any) -> str:
    number = float(value)
    if number == int(number):
        return str(int(number))
    return f"{number:g}"


def _fmt_cashflow_pnl(value: Any) -> Optional[str]:
    number = _as_float(value)
    if number is None:
        return None
    if number < 0:
        return f"-${abs(number):,.2f}"
    return f"${number:,.2f}"


def shorten_wallet(address: str) -> str:
    text = str(address or "")
    if len(text) <= 12:
        return text
    return f"{text[:6]}…{text[-4:]}"


def watch_position_dashboard_line(payload: Optional[Mapping[str, Any]]) -> str:
    """One short watch-header line. No wallet / empty payload is omitted."""
    if not isinstance(payload, Mapping):
        return ""
    wallet = payload.get("wallet")
    if not isinstance(wallet, str) or not wallet.strip():
        return ""
    parts = [f"Wallet: {shorten_wallet(wallet)}"]
    flags = payload.get("quality_flags") or []
    if payload.get("position_error") or "position_unavailable" in flags:
        parts.append("position unavailable")
    elif not payload.get("has_position"):
        parts.append("no position")
    else:
        legs = payload.get("legs")
        if isinstance(legs, list) and legs:
            rendered = []
            for leg in legs:
                if not isinstance(leg, Mapping) or leg.get("shares") is None:
                    continue
                chunk = _fmt_shares(leg["shares"])
                outcome = leg.get("outcome")
                if outcome:
                    chunk = f"{chunk} {outcome}"
                rendered.append(chunk)
            if rendered:
                parts.append(" / ".join(rendered))
        elif payload.get("shares") is not None:
            chunk = _fmt_shares(payload["shares"])
            outcome = payload.get("outcome")
            if outcome:
                chunk = f"{chunk} {outcome}"
            parts.append(chunk)
        else:
            parts.append("no position")
    pnl = payload.get("pnl")
    if pnl is None:
        pnl = payload.get("cashflow")
    pnl_text = _fmt_cashflow_pnl(pnl)
    if pnl_text is not None:
        parts.append(f"cashflow P&L {pnl_text}")
    parts.append("lagged Data API")
    return " | ".join(parts)
