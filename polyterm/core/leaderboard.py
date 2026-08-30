"""Normalize public trader leaderboard rows without fabricating missing stats."""

from typing import Any, Dict, Iterable, List, Optional, Sequence


DATA_API_ENDPOINT = "/v1/leaderboard"
DATA_API_SORTABLE_TYPES = {"profit", "volume"}
DATA_API_VOLUME_ALIASES = {"active"}
DATA_API_UNSUPPORTED_TYPES = {"winrate"}

WINRATE_UNSUPPORTED_MESSAGE = (
    "The public Data API /v1/leaderboard does not rank by win rate. "
    "Use --type profit or --type volume. The agent tool trader.leaderboard "
    "computes win-rate evidence from closed positions and labels that provenance."
)


class UnsupportedLeaderboardType(ValueError):
    """Raised when a leaderboard type cannot be served honestly from the chosen source."""


def data_api_sort_by(board_type: str) -> str:
    """Map a PolyTerm board type to a Data API sort key, or refuse unsupported types."""
    normalized = str(board_type or "").lower()
    if normalized in DATA_API_UNSUPPORTED_TYPES:
        raise UnsupportedLeaderboardType(WINRATE_UNSUPPORTED_MESSAGE)
    if normalized in DATA_API_VOLUME_ALIASES:
        return "volume"
    if normalized in DATA_API_SORTABLE_TYPES:
        return normalized
    raise UnsupportedLeaderboardType(
        f"Unsupported leaderboard type for Data API source: {board_type}"
    )


def _first_present(row: Dict[str, Any], keys: Sequence[str]) -> Any:
    for key in keys:
        if key in row and row[key] not in (None, ""):
            return row[key]
    return None


def _optional_float(row: Dict[str, Any], keys: Sequence[str]) -> Optional[float]:
    value = _first_present(row, keys)
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _optional_int(row: Dict[str, Any], keys: Sequence[str]) -> Optional[int]:
    value = _first_present(row, keys)
    if value is None:
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def normalize_leaderboard_row(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Normalize one public leaderboard row.

    Missing optional stats stay ``None`` instead of being filled with zeros
    that would look like measured win rate, trade count, or average size.
    Rows without a wallet address are dropped.
    """
    if not isinstance(row, dict):
        return None

    address = _first_present(row, ("address", "user", "proxyWallet", "wallet"))
    if not address:
        return None
    address = str(address)

    profit = _optional_float(row, ("profit", "pnl", "cashPnl")) or 0.0
    volume = _optional_float(row, ("volume", "vol", "totalVolume")) or 0.0
    trades = _optional_int(row, ("trades", "tradeCount"))
    win_rate = _optional_float(row, ("winRate", "win_rate"))
    avg_size = _optional_float(row, ("avgSize", "averageTradeSize"))
    if avg_size is None and trades and trades > 0 and volume:
        avg_size = volume / trades

    return {
        "address": address,
        "user_name": str(_first_present(row, ("userName", "username", "name")) or ""),
        "profit": profit,
        "volume": volume,
        "trades": trades,
        "win_rate": win_rate,
        "avg_size": avg_size,
        "rank": row.get("rank"),
    }


def normalize_leaderboard_rows(rows: Iterable[Any], limit: Optional[int] = None) -> List[Dict[str, Any]]:
    """Normalize a list of leaderboard rows, dropping unusable entries."""
    traders: List[Dict[str, Any]] = []
    for row in rows or []:
        normalized = normalize_leaderboard_row(row) if isinstance(row, dict) else None
        if normalized:
            traders.append(normalized)
        if limit is not None and len(traders) >= limit:
            break
    return traders


def sort_traders(traders: List[Dict[str, Any]], board_type: str) -> List[Dict[str, Any]]:
    """Sort normalized traders by an available metric. Missing values sort last."""
    key_map = {
        "profit": "profit",
        "volume": "volume",
        "active": "volume",
        "winrate": "win_rate",
    }
    metric = key_map.get(str(board_type or "").lower(), "profit")

    def sort_key(row: Dict[str, Any]):
        value = row.get(metric)
        if value is None:
            return (1, 0.0)
        return (0, -float(value))

    return sorted(traders, key=sort_key)


def leaderboard_quality_flags(source: str, board_type: str, traders: Sequence[Dict[str, Any]]) -> List[str]:
    """Describe what the rows actually contain so callers do not over-read blanks."""
    flags = []
    if source == "data-api":
        flags.append("data_api_v1_leaderboard")
    elif source == "local":
        flags.append("local_tracked_wallets")
    else:
        flags.append(f"source_{source}")

    if board_type == "active":
        flags.append("active_ranked_by_volume")
    if board_type == "winrate" and source == "data-api":
        flags.append("winrate_unsupported_by_public_leaderboard")

    if traders:
        if all(row.get("profit") is None for row in traders):
            flags.append("profit_not_provided")
        if all(row.get("win_rate") is None for row in traders):
            flags.append("win_rate_not_provided")
        if all(row.get("trades") is None for row in traders):
            flags.append("trade_count_not_provided")
        if all(row.get("avg_size") is None for row in traders):
            flags.append("avg_size_not_provided")
    return flags


def format_trader_label(trader: Dict[str, Any], width: int = 12) -> str:
    """Short wallet label, with username when the Data API provides one."""
    address = str(trader.get("address") or "")
    short = address[:width] + ("..." if len(address) > width else "")
    user_name = trader.get("user_name") or ""
    if user_name:
        return f"{short} ({user_name})"
    return short
