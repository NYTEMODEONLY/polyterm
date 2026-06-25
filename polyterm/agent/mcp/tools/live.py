"""Live Polymarket intelligence tools for agent adapters."""

import time
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from ...contracts import envelope
from ....api.data_api import DataAPIClient
from ....api.gamma import GammaClient
from ....api.market_utils import (
    get_clob_token_ids,
    get_market_condition_id,
    market_probability_price,
    parse_list_field,
)
from ....utils.json_output import safe_float


def top_markets(limit: int = 3, sort: str = "volume24h") -> dict:
    """Return top active markets from live Gamma market data."""
    gamma = GammaClient()
    try:
        markets = gamma.get_trending_markets(limit=max(limit, 1) * 3)
        normalized = [_market_summary(m) for m in markets]
        sort_key = _market_sort_key(sort)
        normalized.sort(key=sort_key, reverse=True)
        return envelope(
            {
                "query": "top active Polymarket markets",
                "sort": sort,
                "count": min(len(normalized), limit),
                "markets": normalized[:limit],
                "quality_flags": ["live_gamma_data", "active_non_closed_markets"],
            },
            meta={"tool": "market.top"},
        )
    finally:
        gamma.close()


def whale_trades(
    limit: int = 5,
    hours: int = 24,
    min_notional: float = 0,
    sample_size: int = 1000,
) -> dict:
    """Return top public trade rows by notional value over a recent window."""
    data_api = DataAPIClient()
    cutoff = int(time.time() - max(hours, 1) * 3600)
    try:
        trades = data_api.get_trades(limit=min(max(sample_size, limit), 10000))
        rows = []
        for trade in trades if isinstance(trades, list) else []:
            normalized = _trade_summary(trade)
            if normalized["timestamp"] < cutoff:
                continue
            if normalized["notional"] < min_notional:
                continue
            rows.append(normalized)
        rows.sort(key=lambda item: item["notional"], reverse=True)
        return envelope(
            {
                "hours": hours,
                "min_notional": min_notional,
                "sample_size": sample_size,
                "count": min(len(rows), limit),
                "trades": rows[:limit],
                "quality_flags": [
                    "live_data_api_trades",
                    "notional=size_times_price",
                    "public_trade_rows_only",
                ],
            },
            meta={"tool": "wallet.whale_trades"},
        )
    finally:
        data_api.close()


def top_traders(
    limit: int = 3,
    hours: int = 72,
    min_win_rate: float = 0.8,
    candidate_count: int = 25,
) -> dict:
    """Return active traders with recent volume and closed-position win-rate evidence."""
    data_api = DataAPIClient()
    cutoff = int(time.time() - max(hours, 1) * 3600)
    try:
        candidates = _recent_trade_candidates(data_api, cutoff, max(candidate_count, limit))
        if len(candidates) < limit:
            candidates.extend(_leaderboard_candidates(data_api, max(candidate_count, limit)))

        seen = set()
        scored = []
        for candidate in candidates:
            address = candidate.get("address", "")
            if not address or address in seen:
                continue
            seen.add(address)
            stats = _closed_position_stats(data_api, address, cutoff)
            if stats["closed_positions"] == 0:
                continue
            if stats["win_rate"] < min_win_rate:
                continue
            scored.append({**candidate, **stats})
            if len(scored) >= max(candidate_count, limit):
                break

        scored.sort(key=lambda item: (item["recent_notional"], item["wins"]), reverse=True)
        return envelope(
            {
                "hours": hours,
                "min_win_rate": min_win_rate,
                "count": min(len(scored), limit),
                "traders": scored[:limit],
                "quality_flags": [
                    "live_data_api_trades",
                    "win_rate_from_recent_closed_positions",
                    "candidate_pool_limited",
                ],
            },
            meta={"tool": "trader.leaderboard"},
        )
    finally:
        data_api.close()


def market_movers(
    limit: int = 3,
    hours: int = 48,
    min_abs_change: float = 0.05,
) -> dict:
    """Return active markets with the largest available price moves."""
    gamma = GammaClient()
    try:
        markets = gamma.get_markets(limit=500, active=True, closed=False)
        movers = []
        for market in markets:
            summary = _market_summary(market)
            change = _market_change(market)
            if abs(change) < min_abs_change:
                continue
            previous = summary["probability"] - change if summary["probability"] is not None else None
            flipped = (
                previous is not None
                and ((previous < 0.5 <= summary["probability"]) or (previous > 0.5 >= summary["probability"]))
            )
            movers.append({
                **summary,
                "available_price_change": change,
                "previous_probability_estimate": previous,
                "flipped_50_percent": flipped,
            })

        movers.sort(key=lambda item: abs(item["available_price_change"]), reverse=True)
        return envelope(
            {
                "requested_hours": hours,
                "count": min(len(movers), limit),
                "markets": movers[:limit],
                "quality_flags": [
                    "live_gamma_data",
                    "change_window_uses_available_gamma_change_fields",
                ],
            },
            meta={"tool": "market.movers"},
        )
    finally:
        gamma.close()


def _market_summary(market: Dict[str, Any]) -> Dict[str, Any]:
    probability = market_probability_price(market)
    return {
        "gamma_market_id": str(market.get("id") or ""),
        "gamma_slug": market.get("slug") or "",
        "condition_id": get_market_condition_id(market),
        "clob_token_ids": get_clob_token_ids(market),
        "question": market.get("question") or market.get("title") or "",
        "event_slug": market.get("event_slug") or market.get("eventSlug") or "",
        "probability": probability,
        "outcomes": parse_list_field(market.get("outcomes")),
        "outcome_prices": parse_list_field(market.get("outcomePrices")),
        "volume_24h": safe_float(market.get("volume24hr") or market.get("volume24h")),
        "volume": safe_float(market.get("volume")),
        "liquidity": safe_float(market.get("liquidity")),
        "last_trade_price": safe_float(market.get("lastTradePrice")),
        "best_bid": safe_float(market.get("bestBid")),
        "best_ask": safe_float(market.get("bestAsk")),
        "end_date": market.get("endDate") or market.get("end_date_iso") or "",
        "active": bool(market.get("active", True)),
        "closed": bool(market.get("closed", False)),
    }


def _trade_summary(trade: Dict[str, Any]) -> Dict[str, Any]:
    size = safe_float(trade.get("size"))
    price = safe_float(trade.get("price"))
    timestamp = int(safe_float(trade.get("timestamp"), 0))
    return {
        "wallet": trade.get("proxyWallet") or trade.get("user") or trade.get("trader") or "",
        "name": trade.get("name") or trade.get("pseudonym") or "",
        "side": trade.get("side") or "",
        "asset": str(trade.get("asset") or ""),
        "condition_id": trade.get("conditionId") or "",
        "size": size,
        "price": price,
        "notional": size * price,
        "timestamp": timestamp,
        "timestamp_iso": _timestamp_iso(timestamp),
        "market_title": trade.get("title") or "",
        "market_slug": trade.get("slug") or "",
        "event_slug": trade.get("eventSlug") or "",
        "outcome": trade.get("outcome") or "",
        "outcome_index": trade.get("outcomeIndex"),
        "transaction_hash": trade.get("transactionHash") or "",
    }


def _recent_trade_candidates(data_api: DataAPIClient, cutoff: int, limit: int) -> List[Dict[str, Any]]:
    trades = data_api.get_trades(limit=min(max(limit * 20, 100), 10000))
    grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "address": "",
        "user_name": "",
        "recent_trades": 0,
        "recent_notional": 0.0,
    })
    for trade in trades if isinstance(trades, list) else []:
        summary = _trade_summary(trade)
        if summary["timestamp"] < cutoff:
            continue
        address = summary["wallet"]
        if not address:
            continue
        row = grouped[address]
        row["address"] = address
        row["user_name"] = summary["name"]
        row["recent_trades"] += 1
        row["recent_notional"] += summary["notional"]
    candidates = list(grouped.values())
    candidates.sort(key=lambda item: item["recent_notional"], reverse=True)
    return candidates[:limit]


def _leaderboard_candidates(data_api: DataAPIClient, limit: int) -> List[Dict[str, Any]]:
    candidates = []
    for row in data_api.get_leaderboard(period="7d", limit=min(limit, 50), sort_by="volume"):
        address = row.get("proxyWallet") or row.get("address") or row.get("user") or ""
        candidates.append({
            "address": address,
            "user_name": row.get("userName") or row.get("name") or "",
            "recent_trades": 0,
            "recent_notional": safe_float(row.get("vol") or row.get("volume")),
            "leaderboard_rank": row.get("rank"),
            "leaderboard_pnl": safe_float(row.get("pnl")),
        })
    return candidates


def _closed_position_stats(data_api: DataAPIClient, address: str, cutoff: int) -> Dict[str, Any]:
    positions = data_api.get_closed_positions(address, limit=50, sort_by="REALIZEDPNL")
    recent = []
    for position in positions:
        timestamp = int(safe_float(position.get("timestamp"), 0))
        if timestamp and timestamp < cutoff:
            continue
        recent.append(position)
    wins = 0
    losses = 0
    realized_pnl = 0.0
    for position in recent:
        pnl = safe_float(position.get("realizedPnl") or position.get("cashPnl"))
        realized_pnl += pnl
        if pnl > 0:
            wins += 1
        else:
            losses += 1
    total = wins + losses
    return {
        "closed_positions": total,
        "wins": wins,
        "losses": losses,
        "win_rate": wins / total if total else 0.0,
        "realized_pnl": realized_pnl,
    }


def _market_sort_key(sort: str):
    key = str(sort).lower()
    if key in {"liquidity", "liq"}:
        return lambda market: market["liquidity"]
    if key in {"volume", "volume_total"}:
        return lambda market: market["volume"]
    return lambda market: market["volume_24h"]


def _market_change(market: Dict[str, Any]) -> float:
    for key in ("oneDayPriceChange", "priceChange24h", "price_change_24h"):
        value = market.get(key)
        if value is not None:
            return safe_float(value)
    current = market_probability_price(market)
    previous = safe_float(market.get("price24hAgo"))
    if previous:
        return current - previous
    return 0.0


def _timestamp_iso(timestamp: int) -> str:
    if not timestamp:
        return ""
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat()
