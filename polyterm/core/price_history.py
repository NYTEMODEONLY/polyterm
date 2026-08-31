"""CLOB-backed price history series. Demo random-walk is opt-in and labeled."""

import hashlib
import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


SOURCE_CLOB = "clob_prices_history"
SOURCE_DEMO = "demo_random_walk"
SOURCE_NONE = "none"

PERIOD_HOURS = {
    "day": 24,
    "week": 168,
    "month": 720,
    "all": 2160,
}

DEMO_DISCLOSURE = (
    "DEMO SERIES: this is a seeded random walk, not Polymarket CLOB or Gamma "
    "historical prices. Highs, lows, volatility, and the chart are invented. "
    "Do not treat this as market history."
)

HISTORY_UNAVAILABLE = (
    "No CLOB price history is available for this market. "
    "polyterm history does not invent a price path. "
    "Pass --demo for a labeled random-walk series, or pick a market with CLOB token IDs."
)

MISSING_TOKEN_IDS = (
    "This market has no CLOB token IDs, so GET /prices-history cannot be called. "
    "polyterm history does not invent a price path. Pass --demo for a labeled "
    "random-walk series."
)


def period_to_hours(period: str) -> int:
    """Map a history CLI period to a lookback window in hours."""
    return PERIOD_HOURS.get(period, PERIOD_HOURS["week"])


def select_clob_granularity(hours: int) -> Tuple[str, int]:
    """Pick CLOB interval/fidelity for a lookback window."""
    if hours <= 1:
        return "1h", 60
    if hours <= 6:
        return "6h", 60
    if hours <= 24:
        return "1d", 300
    return "max", 3600


def build_time_bounds(hours: int, now: Optional[datetime] = None) -> Tuple[int, int]:
    """Build inclusive [start, end] unix timestamps for the requested window."""
    safe_hours = max(int(hours), 1)
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    end_ts = int(now.timestamp())
    return end_ts - (safe_hours * 3600), end_ts


def parse_clob_history_rows(
    history: Optional[List[Dict[str, Any]]],
    start_ts: int,
    end_ts: int,
) -> List[Dict[str, Any]]:
    """Convert CLOB /prices-history rows into sorted price points in-window."""
    points: List[Dict[str, Any]] = []
    for row in history or []:
        if not isinstance(row, dict) or "t" not in row or "p" not in row:
            continue
        timestamp = _as_int(row.get("t"))
        price = _as_float(row.get("p"))
        if timestamp is None or price is None:
            continue
        if timestamp < start_ts or timestamp > end_ts:
            continue
        moment = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        points.append(
            {
                "timestamp": moment.isoformat(),
                "date": moment.strftime("%m/%d"),
                "price": price,
            }
        )
    points.sort(key=lambda point: point["timestamp"])
    return points


def summarize_series(
    points: List[Dict[str, Any]],
    *,
    current_price: Optional[float] = None,
    volume_24h: float = 0.0,
    reported_volume: float = 0.0,
) -> Dict[str, Any]:
    """Derive summary, milestones, and trend from a real or labeled price series."""
    prices = [float(point["price"]) for point in points]
    if not prices:
        last_price = current_price if current_price is not None else 0.0
        return {
            "current": {
                "price": last_price,
                "volume_24h": volume_24h,
            },
            "summary": {
                "price_change": 0.0,
                "high": last_price,
                "low": last_price,
                "volatility": 0.0,
                "reported_volume": reported_volume,
                "volume_note": "Gamma snapshot, not period volume from the series",
            },
            "points": [],
            "milestones": [],
            "trend": {"direction": "sideways", "strength": ""},
        }

    last_price = prices[-1] if current_price is None else current_price
    high = max(prices)
    low = min(prices)
    start_price = prices[0]
    avg = sum(prices) / len(prices)
    volatility = (sum((price - avg) ** 2 for price in prices) / len(prices)) ** 0.5

    return {
        "current": {
            "price": last_price,
            "volume_24h": volume_24h,
        },
        "summary": {
            "price_change": last_price - start_price,
            "high": high,
            "low": low,
            "volatility": volatility,
            "reported_volume": reported_volume,
            "volume_note": "Gamma snapshot, not period volume from the series",
        },
        "points": points,
        "milestones": _milestones(points, prices, high, low),
        "trend": _trend(prices),
    }


def build_clob_payload(
    points: List[Dict[str, Any]],
    *,
    market_title: str,
    period: str,
    hours: int,
    token_id: str,
    current_price: Optional[float] = None,
    volume_24h: float = 0.0,
    reported_volume: float = 0.0,
    gamma_market_id: Optional[str] = None,
) -> Dict[str, Any]:
    """JSON/table payload for a CLOB-backed series."""
    series = summarize_series(
        points,
        current_price=current_price if current_price is not None else points[-1]["price"],
        volume_24h=volume_24h,
        reported_volume=reported_volume,
    )
    return {
        "success": True,
        "mode": SOURCE_CLOB,
        "source": SOURCE_CLOB,
        "uses_historical_data": True,
        "market": market_title,
        "gamma_market_id": gamma_market_id,
        "clob_token_id": token_id,
        "period": period,
        "hours": hours,
        "point_count": len(points),
        "history": series,
    }


def build_demo_payload(
    *,
    market_title: str,
    period: str,
    current_price: float,
    volume_24h: float = 0.0,
    reported_volume: float = 0.0,
    seed_key: str = "",
    gamma_market_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Labeled random-walk payload. Not CLOB/Gamma historical prices."""
    hours = period_to_hours(period)
    points = build_demo_points(current_price, hours, seed_key=seed_key or market_title)
    series = summarize_series(
        points,
        current_price=current_price,
        volume_24h=volume_24h,
        reported_volume=reported_volume,
    )
    return {
        "success": True,
        "mode": SOURCE_DEMO,
        "source": SOURCE_DEMO,
        "uses_historical_data": False,
        "disclosure": DEMO_DISCLOSURE,
        "market": market_title,
        "gamma_market_id": gamma_market_id,
        "period": period,
        "hours": hours,
        "point_count": len(points),
        "history": series,
    }


def build_demo_points(
    current_price: float,
    hours: int,
    seed_key: str = "",
    now: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Seeded random walk ending at current_price. Invented, not historical."""
    rng = random.Random(_demo_seed(seed_key))
    days = max(int(hours) // 24, 1)
    if now is None:
        now = datetime.now(timezone.utc)
    elif now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)

    points: List[Dict[str, Any]] = []
    price = current_price
    for remaining in range(days, -1, -1):
        moment = now - timedelta(days=remaining)
        if remaining > 0:
            price = max(0.05, min(0.95, price - rng.uniform(-0.03, 0.03)))
        point_price = current_price if remaining == 0 else price
        points.append(
            {
                "timestamp": moment.isoformat(),
                "date": moment.strftime("%m/%d"),
                "price": point_price,
            }
        )
    points[-1]["price"] = current_price
    return points


def refuse_payload(error: str, hint: Optional[str] = None) -> Dict[str, Any]:
    """Machine-readable refusal: no invented series."""
    payload = {
        "success": False,
        "error": error,
        "mode": "unavailable",
        "source": SOURCE_NONE,
        "uses_historical_data": False,
        "hint": hint or "pass --demo to run a labeled random-walk series",
    }
    return payload


def _milestones(
    points: List[Dict[str, Any]],
    prices: List[float],
    high: float,
    low: float,
) -> List[Dict[str, str]]:
    milestones: List[Dict[str, str]] = []
    high_idx = prices.index(high)
    low_idx = prices.index(low)
    milestones.append(
        {
            "type": "high",
            "date": points[high_idx]["date"],
            "description": f"Period high at {high:.1%}",
        }
    )
    milestones.append(
        {
            "type": "low",
            "date": points[low_idx]["date"],
            "description": f"Period low at {low:.1%}",
        }
    )
    for index in range(1, len(points)):
        change = points[index]["price"] - points[index - 1]["price"]
        if abs(change) <= 0.05:
            continue
        move_type = "surge" if change > 0 else "drop"
        milestones.append(
            {
                "type": move_type,
                "date": points[index]["date"],
                "description": f"{'Surged' if change > 0 else 'Dropped'} {abs(change):.1%}",
            }
        )
    milestones.sort(key=lambda item: item["type"] in ["high", "low"], reverse=True)
    return milestones


def _trend(prices: List[float]) -> Dict[str, str]:
    if len(prices) < 2:
        return {"direction": "sideways", "strength": ""}
    window = min(3, len(prices))
    recent_avg = sum(prices[-window:]) / window
    older_avg = sum(prices[:window]) / window
    if recent_avg > older_avg * 1.03:
        return {
            "direction": "up",
            "strength": "steadily" if recent_avg < older_avg * 1.10 else "strongly",
        }
    if recent_avg < older_avg * 0.97:
        return {
            "direction": "down",
            "strength": "steadily" if recent_avg > older_avg * 0.90 else "sharply",
        }
    return {"direction": "sideways", "strength": ""}


def _demo_seed(seed_key: str) -> int:
    digest = hashlib.md5(str(seed_key).encode("utf-8")).hexdigest()
    return 42 + int(digest[:8], 16)


def _as_float(value: Any) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None
