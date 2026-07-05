"""Wallet intelligence built from Polymarket Data API and local state."""

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from ..api.data_api import DataAPIClient
from ..db.database import Database
from ..db.models import Trade, Wallet


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or default)
    except (TypeError, ValueError):
        return default


def _position_value(position: Dict[str, Any]) -> float:
    return max(
        _as_float(position.get("currentValue")),
        _as_float(position.get("value")),
        _as_float(position.get("initialValue")),
        _as_float(position.get("cashPnl")) + _as_float(position.get("initialValue")),
    )


def _smart_money_profile(wallet: Wallet, min_trades: int) -> Dict[str, Any]:
    """Return agent-readable smart-money ranking details for one wallet."""
    now = datetime.now()
    updated_at = wallet.updated_at
    recency_days = max((now - updated_at).days, 0) if updated_at else None
    is_whale = wallet.total_volume >= 100000 or wallet.largest_trade >= 50000
    market_focus = list(wallet.favorite_markets or [])[:5]
    noisy_reasons: List[str] = []

    if wallet.total_trades < max(min_trades * 2, min_trades + 5):
        noisy_reasons.append("limited_trade_sample")
    if wallet.risk_score >= 70:
        noisy_reasons.append("high_wallet_risk_score")
    if wallet.win_rate >= 0.95 and wallet.total_trades < 25:
        noisy_reasons.append("very_high_hit_rate_small_sample")

    hit_rate_component = wallet.win_rate * 40
    trade_depth_component = min(wallet.total_trades / max(min_trades, 1), 3.0) / 3.0 * 20
    volume_component = min(wallet.total_volume / 250000, 1.0) * 15
    recency_component = _recency_component(recency_days)
    focus_component = min(len(market_focus), 5) / 5 * 5
    risk_penalty = min(max(wallet.risk_score, 0), 100) / 100 * 15
    smart_money_score = max(
        hit_rate_component
        + trade_depth_component
        + volume_component
        + recency_component
        + focus_component
        - risk_penalty,
        0,
    )

    return {
        "smart_money_score": round(smart_money_score, 6),
        "wallet_role": "smart_money_whale" if is_whale else "smart_money",
        "is_whale": is_whale,
        "is_noisy": bool(noisy_reasons),
        "noisy_reasons": noisy_reasons,
        "ranking_inputs": {
            "hit_rate": wallet.win_rate,
            "trade_count": wallet.total_trades,
            "total_volume": wallet.total_volume,
            "largest_trade": wallet.largest_trade,
            "recency_days": recency_days,
            "market_focus": market_focus,
            "risk_score": wallet.risk_score,
            "realized_pnl": None,
            "realized_pnl_available": False,
        },
        "explanation": _smart_money_explanation(wallet, is_whale, noisy_reasons),
    }


def _recency_component(recency_days: Optional[int]) -> float:
    if recency_days is None:
        return 0.0
    if recency_days <= 7:
        return 10.0
    if recency_days <= 30:
        return 6.0
    if recency_days <= 90:
        return 3.0
    return 0.0


def _smart_money_explanation(wallet: Wallet, is_whale: bool, noisy_reasons: List[str]) -> str:
    parts = [
        f"Win rate {wallet.win_rate:.0%} over {wallet.total_trades} trade(s)",
        f"volume ${wallet.total_volume:,.0f}",
    ]
    if is_whale:
        parts.append("also qualifies as whale-sized flow")
    if wallet.favorite_markets:
        parts.append(f"focus markets: {', '.join(wallet.favorite_markets[:3])}")
    if noisy_reasons:
        parts.append(f"caveats: {', '.join(noisy_reasons)}")
    return "; ".join(parts) + "."


class WalletIntelligence:
    """Analyze public and locally observed wallet behavior."""

    def __init__(
        self,
        data_api: Optional[DataAPIClient] = None,
        database: Optional[Database] = None,
    ):
        self.data_api = data_api or DataAPIClient()
        self.db = database or Database()

    def analyze_wallet(self, address: str, limit: int = 100, refresh: bool = True) -> Dict[str, Any]:
        """Return a wallet intelligence profile."""
        positions: List[Dict[str, Any]] = []
        trades: List[Dict[str, Any]] = []
        value: Dict[str, Any] = {}
        errors: List[str] = []

        if refresh:
            try:
                profile = self.data_api.get_wallet_profile(address, trades_limit=limit, positions_limit=limit)
                positions = profile.get("positions", [])
                trades = profile.get("trades", [])
                value = profile.get("value", {})
            except Exception as exc:
                errors.append(f"Data API profile unavailable: {exc}")

        local_wallet = self.db.get_wallet(address)
        local_stats = self.db.get_wallet_stats(address) if local_wallet else {}

        metrics = self._compute_metrics(positions, trades)
        tags = self._tags_for(metrics, local_wallet)

        if local_wallet is None:
            local_wallet = Wallet(
                address=address,
                first_seen=datetime.now(),
                total_trades=metrics["trade_count"],
                total_volume=metrics["total_volume"],
                win_rate=metrics["win_rate"],
                avg_position_size=metrics["avg_trade_size"],
                tags=tags,
                largest_trade=metrics["largest_trade"],
            )
        else:
            local_wallet.total_trades = max(local_wallet.total_trades, metrics["trade_count"])
            local_wallet.total_volume = max(local_wallet.total_volume, metrics["total_volume"])
            local_wallet.win_rate = max(local_wallet.win_rate, metrics["win_rate"])
            local_wallet.avg_position_size = max(local_wallet.avg_position_size, metrics["avg_trade_size"])
            local_wallet.largest_trade = max(local_wallet.largest_trade, metrics["largest_trade"])
            for tag in tags:
                if tag not in local_wallet.tags:
                    local_wallet.tags.append(tag)
            local_wallet.updated_at = datetime.now()

        if refresh and (positions or trades):
            self.db.upsert_wallet(local_wallet)

        return {
            "address": address,
            "source": {
                "positions": "data-api" if positions else "none",
                "trades": "data-api" if trades else "none",
                "local_wallet": bool(local_stats),
            },
            "metrics": metrics,
            "value": value,
            "positions": positions[:limit],
            "recent_trades": trades[:limit],
            "local_stats": local_stats,
            "tags": local_wallet.tags,
            "quality_flags": self._quality_flags(positions, trades, errors),
            "errors": errors,
        }

    def local_whales(self, min_notional: float = 10000, hours: int = 24) -> Dict[str, Any]:
        """Return locally observed whale trades and wallet summaries."""
        trades = self.db.get_large_trades(min_notional=min_notional, hours=hours)
        by_wallet: Dict[str, Dict[str, Any]] = {}
        for trade in trades:
            item = by_wallet.setdefault(
                trade.wallet_address,
                {
                    "address": trade.wallet_address,
                    "trade_count": 0,
                    "notional": 0.0,
                    "largest_trade": 0.0,
                    "markets": Counter(),
                    "trades": [],
                },
            )
            item["trade_count"] += 1
            item["notional"] += trade.notional
            item["largest_trade"] = max(item["largest_trade"], trade.notional)
            item["markets"][trade.market_id] += 1
            item["trades"].append(trade.to_dict())

        wallets = []
        for item in by_wallet.values():
            item["top_markets"] = item["markets"].most_common(5)
            item.pop("markets", None)
            wallets.append(item)
        wallets.sort(key=lambda row: row["notional"], reverse=True)

        return {
            "hours": hours,
            "min_notional": min_notional,
            "wallet_count": len(wallets),
            "trade_count": len(trades),
            "wallets": wallets,
            "quality_flags": [
                "local_db_only",
                "trade_direction_may_be_inferred",
            ],
        }

    def smart_money(self, min_win_rate: float = 0.70, min_trades: int = 10, limit: int = 20) -> Dict[str, Any]:
        """Return locally identified high win-rate wallets ranked for agent use."""
        wallets = self.db.get_smart_money_wallets(min_win_rate=min_win_rate, min_trades=min_trades)
        rows: List[Dict[str, Any]] = []
        for wallet in wallets:
            row = wallet.to_dict()
            edge_score = wallet.win_rate * min(wallet.total_trades / max(min_trades, 1), 3.0)
            row["edge_score"] = round(edge_score, 6)
            row.update(_smart_money_profile(wallet, min_trades=min_trades))
            row["is_smart_money"] = True
            rows.append(row)

        rows.sort(
            key=lambda row: (
                _as_float(row.get("smart_money_score")),
                _as_float(row.get("edge_score")),
                _as_float(row.get("total_volume")),
                int(row.get("total_trades") or 0),
            ),
            reverse=True,
        )
        displayed = rows[:limit]

        return {
            "source": "local_db",
            "min_win_rate": min_win_rate,
            "min_trades": min_trades,
            "wallet_count": len(rows),
            "wallets": displayed,
            "quality_flags": ["local_db_smart_money", "requires_recent_refresh_for_live_flow"],
        }

    def whale_trades(
        self,
        min_notional: float = 10000,
        hours: int = 48,
        limit: int = 3,
        market: Optional[str] = None,
        sample_size: int = 3000,
        now: Optional[datetime] = None,
        page_size: int = 1000,
    ) -> Dict[str, Any]:
        """Return top public trade rows ranked by cash notional.

        This is the deterministic answer path for prompts such as "biggest whale
        wagers in the last 48 hours". It scans the Data API public trade tape
        with server-side CASH filtering, filters the requested time window, then
        sorts client-side by ``size * price`` instead of trusting the API's
        recency order.
        """
        now_dt = now or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        cutoff = now_dt - timedelta(hours=hours)
        cutoff_ts = int(cutoff.timestamp())

        page_size = max(1, min(int(page_size or 1000), 1000))
        sample_size = max(page_size, int(sample_size or page_size))
        max_offset = max(sample_size - page_size, 0)

        trades: List[Dict[str, Any]] = []
        errors: List[Dict[str, Any]] = []
        pages_scanned = 0
        rows_scanned = 0
        stopped_at_cutoff = False

        for offset in range(0, max_offset + 1, page_size):
            try:
                page = self.data_api.get_recent_trades(
                    limit=page_size,
                    offset=offset,
                    filter_type="CASH",
                    filter_amount=min_notional,
                )
            except Exception as exc:
                errors.append({"offset": offset, "error": str(exc)})
                break

            pages_scanned += 1
            if not page:
                stopped_at_cutoff = True
                break

            page_timestamps = []
            rows_scanned += len(page)
            for raw in page:
                timestamp = int(_as_float(raw.get("timestamp"), 0))
                if timestamp:
                    page_timestamps.append(timestamp)
                if timestamp and timestamp < cutoff_ts:
                    continue

                identifiers = {
                    str(raw.get("conditionId") or ""),
                    str(raw.get("slug") or ""),
                    str(raw.get("eventSlug") or ""),
                    str(raw.get("asset") or ""),
                }
                if market and market not in identifiers:
                    continue

                size = _as_float(raw.get("size"), 0.0)
                price = _as_float(raw.get("price"), 0.0)
                notional = size * price
                if notional < min_notional:
                    continue

                trades.append({
                    "wallet": raw.get("proxyWallet") or raw.get("user") or raw.get("wallet"),
                    "name": raw.get("name"),
                    "side": raw.get("side"),
                    "asset": raw.get("asset"),
                    "condition_id": raw.get("conditionId"),
                    "size": size,
                    "price": price,
                    "notional": notional,
                    "timestamp": timestamp,
                    "timestamp_iso": datetime.fromtimestamp(timestamp, timezone.utc).isoformat() if timestamp else None,
                    "market_title": raw.get("title"),
                    "market_slug": raw.get("slug"),
                    "event_slug": raw.get("eventSlug"),
                    "outcome": raw.get("outcome"),
                    "outcome_index": raw.get("outcomeIndex"),
                    "transaction_hash": raw.get("transactionHash"),
                })

            if page_timestamps and min(page_timestamps) < cutoff_ts:
                stopped_at_cutoff = True
                break

        trades.sort(key=lambda row: (row["notional"], row.get("timestamp") or 0), reverse=True)
        quality_flags = ["live_data_api_trades", "notional=size_times_price", "notional_desc_sorted", "public_trade_rows_only"]
        if errors:
            quality_flags.append("data_api_page_error")
        if not stopped_at_cutoff:
            quality_flags.append("data_api_recent_tape_window_limited")

        return {
            "hours": hours,
            "min_notional": min_notional,
            "sample_size": sample_size,
            "cutoff": cutoff.isoformat(),
            "count": len(trades),
            "rows_scanned": rows_scanned,
            "pages_scanned": pages_scanned,
            "errors": errors,
            "trades": trades[:limit],
            "quality_flags": quality_flags,
        }

    def live_whales(
        self,
        min_notional: float = 10000,
        hours: int = 24,
        limit: int = 20,
        market: Optional[str] = None,
        now: Optional[datetime] = None,
        page_size: int = 100,
        max_offset: int = 3000,
    ) -> Dict[str, Any]:
        """Return public Data API whale trades and wallet rollups.

        This is the agent-facing whale query path: it answers questions like
        "which whale wallets placed bets over $100k in the last 72 hours" from
        the public trade tape instead of relying on PolyTerm's local cache.
        """
        now_dt = now or datetime.now(timezone.utc)
        if now_dt.tzinfo is None:
            now_dt = now_dt.replace(tzinfo=timezone.utc)
        cutoff = now_dt - timedelta(hours=hours)
        cutoff_ts = int(cutoff.timestamp())

        trades: List[Dict[str, Any]] = []
        pages_scanned = 0
        rows_scanned = 0
        stopped_at_cutoff = False

        for offset in range(0, max_offset + 1, page_size):
            page = self.data_api.get_recent_trades(
                limit=page_size,
                offset=offset,
                filter_type="CASH",
                filter_amount=min_notional,
            )
            pages_scanned += 1
            if not page:
                break
            rows_scanned += len(page)

            page_timestamps = []
            for raw in page:
                timestamp = int(_as_float(raw.get("timestamp"), 0))
                if timestamp:
                    page_timestamps.append(timestamp)
                if timestamp and timestamp < cutoff_ts:
                    continue

                identifiers = {
                    str(raw.get("conditionId") or ""),
                    str(raw.get("slug") or ""),
                    str(raw.get("eventSlug") or ""),
                    str(raw.get("asset") or ""),
                }
                if market and market not in identifiers:
                    continue

                size = _as_float(raw.get("size"), 0.0)
                price = _as_float(raw.get("price"), 0.0)
                notional = size * price
                if notional < min_notional:
                    continue

                trades.append({
                    "wallet": raw.get("proxyWallet") or raw.get("user") or raw.get("wallet"),
                    "side": raw.get("side"),
                    "market_title": raw.get("title"),
                    "slug": raw.get("slug"),
                    "condition_id": raw.get("conditionId"),
                    "asset": raw.get("asset"),
                    "outcome": raw.get("outcome"),
                    "size": size,
                    "price": price,
                    "notional": notional,
                    "timestamp": timestamp,
                    "transaction_hash": raw.get("transactionHash"),
                })

            if page_timestamps and min(page_timestamps) < cutoff_ts:
                stopped_at_cutoff = True
                break

        trades.sort(key=lambda row: (row["notional"], row["timestamp"]), reverse=True)
        displayed_trades = trades[:limit]

        by_wallet: Dict[str, Dict[str, Any]] = {}
        for trade in trades:
            wallet = str(trade.get("wallet") or "unknown")
            item = by_wallet.setdefault(
                wallet,
                {
                    "address": wallet,
                    "trade_count": 0,
                    "notional": 0.0,
                    "largest_trade": 0.0,
                    "markets": Counter(),
                    "trades": [],
                },
            )
            item["trade_count"] += 1
            item["notional"] += trade["notional"]
            item["largest_trade"] = max(item["largest_trade"], trade["notional"])
            item["markets"][trade.get("slug") or trade.get("condition_id") or "unknown"] += 1
            item["trades"].append(trade)

        wallets = []
        for item in by_wallet.values():
            item["top_markets"] = item["markets"].most_common(5)
            item.pop("markets", None)
            wallets.append(item)
        wallets.sort(key=lambda row: row["notional"], reverse=True)
        displayed_wallets = wallets[:limit]
        cached_trade_count = self._cache_live_whale_results(trades, wallets)

        quality_flags = ["public_data_api", "trade_direction_may_be_inferred"]
        if not stopped_at_cutoff:
            quality_flags.append("data_api_recent_tape_window_limited")

        return {
            "source": "public_data_api",
            "hours": hours,
            "min_notional": min_notional,
            "cutoff": cutoff.isoformat(),
            "trade_count": len(trades),
            "wallet_count": len(wallets),
            "rows_scanned": rows_scanned,
            "pages_scanned": pages_scanned,
            "cached_trade_count": cached_trade_count,
            "wallets": displayed_wallets,
            "trades": displayed_trades,
            "quality_flags": quality_flags,
        }

    def _cache_live_whale_results(self, trades: List[Dict[str, Any]], wallets: List[Dict[str, Any]]) -> int:
        """Persist live Data API whale query results into the local SQLite cache."""
        cached = 0
        for item in wallets:
            address = str(item.get("address") or "")
            if not address or address == "unknown":
                continue
            favorite_markets = [market for market, _count in item.get("top_markets", [])]
            trade_count = int(item.get("trade_count") or 0)
            total_volume = _as_float(item.get("notional"))
            largest_trade = _as_float(item.get("largest_trade"))
            existing = self.db.get_wallet(address) if hasattr(self.db, "get_wallet") else None
            tags = set(existing.tags if existing else [])
            tags.add("whale")
            wallet = existing or Wallet(address=address, first_seen=datetime.now())
            wallet.total_trades = max(wallet.total_trades, trade_count)
            wallet.total_volume = max(wallet.total_volume, total_volume)
            wallet.avg_position_size = max(
                wallet.avg_position_size,
                total_volume / trade_count if trade_count else 0.0,
            )
            wallet.largest_trade = max(wallet.largest_trade, largest_trade)
            wallet.favorite_markets = sorted(set(wallet.favorite_markets) | set(favorite_markets))
            wallet.tags = sorted(tags)
            wallet.updated_at = datetime.now()
            self.db.upsert_wallet(wallet)

        for trade in trades:
            wallet = str(trade.get("wallet") or "unknown")
            if not wallet or wallet == "unknown":
                continue
            timestamp = trade.get("timestamp")
            if isinstance(timestamp, (int, float)) and timestamp:
                trade_time = datetime.fromtimestamp(timestamp)
            else:
                trade_time = datetime.now()

            self.db.insert_trade(
                Trade(
                    market_id=str(trade.get("condition_id") or trade.get("slug") or trade.get("asset") or ""),
                    market_slug=str(trade.get("slug") or ""),
                    wallet_address=wallet,
                    side=str(trade.get("side") or ""),
                    outcome=str(trade.get("outcome") or ""),
                    price=_as_float(trade.get("price")),
                    size=_as_float(trade.get("size")),
                    notional=_as_float(trade.get("notional")),
                    timestamp=trade_time,
                    tx_hash=str(trade.get("transaction_hash") or ""),
                    taker_address=wallet,
                )
            )
            cached += 1

        return cached

    def consensus_moves(self, trades: List[Dict[str, Any]], min_wallets: int = 3) -> List[Dict[str, Any]]:
        """Find markets where multiple wallets recently traded the same outcome."""
        grouped: Dict[str, Dict[str, Any]] = defaultdict(lambda: {"wallets": set(), "notional": 0.0, "outcomes": Counter()})
        for trade in trades:
            market = str(trade.get("market") or trade.get("market_id") or trade.get("conditionId") or "")
            wallet = str(trade.get("user") or trade.get("proxyWallet") or trade.get("wallet") or "")
            if not market or not wallet:
                continue
            item = grouped[market]
            item["wallets"].add(wallet)
            item["notional"] += _as_float(trade.get("size")) * _as_float(trade.get("price"), 1.0)
            item["outcomes"][str(trade.get("outcome") or trade.get("side") or "unknown")] += 1

        moves = []
        for market, item in grouped.items():
            if len(item["wallets"]) >= min_wallets:
                moves.append({
                    "market": market,
                    "wallet_count": len(item["wallets"]),
                    "notional": item["notional"],
                    "top_outcome": item["outcomes"].most_common(1)[0][0],
                })
        return sorted(moves, key=lambda row: row["notional"], reverse=True)

    def _compute_metrics(self, positions: List[Dict[str, Any]], trades: List[Dict[str, Any]]) -> Dict[str, Any]:
        position_values = [_position_value(pos) for pos in positions]
        total_position_value = sum(position_values)
        largest_position = max(position_values, default=0.0)
        concentration = largest_position / total_position_value if total_position_value else 0.0

        total_pnl = sum(_as_float(pos.get("cashPnl", pos.get("pnl"))) for pos in positions)
        wins = sum(1 for pos in positions if _as_float(pos.get("cashPnl", pos.get("pnl"))) > 0)
        losses = sum(1 for pos in positions if _as_float(pos.get("cashPnl", pos.get("pnl"))) < 0)
        win_rate = wins / (wins + losses) if wins + losses else 0.0

        trade_sizes = [
            _as_float(t.get("size"), 0.0) * max(_as_float(t.get("price"), 1.0), 0.0)
            for t in trades
        ]
        total_volume = sum(trade_sizes)

        categories = Counter(str(pos.get("category") or pos.get("eventSlug") or "unknown") for pos in positions)
        markets = Counter(str(pos.get("market") or pos.get("conditionId") or pos.get("marketId") or "unknown") for pos in positions)

        return {
            "position_count": len(positions),
            "trade_count": len(trades),
            "total_position_value": total_position_value,
            "largest_position": largest_position,
            "position_concentration": concentration,
            "total_pnl": total_pnl,
            "win_rate": win_rate,
            "total_volume": total_volume,
            "avg_trade_size": total_volume / len(trade_sizes) if trade_sizes else 0.0,
            "largest_trade": max(trade_sizes, default=0.0),
            "top_categories": categories.most_common(5),
            "top_markets": markets.most_common(5),
        }

    def _tags_for(self, metrics: Dict[str, Any], wallet: Optional[Wallet]) -> List[str]:
        tags = set(wallet.tags if wallet else [])
        if metrics["total_volume"] >= 100000 or metrics["largest_trade"] >= 50000:
            tags.add("whale")
        if metrics["win_rate"] >= 0.70 and metrics["trade_count"] >= 10:
            tags.add("smart_money")
        if metrics["position_concentration"] >= 0.70 and metrics["total_position_value"] > 10000:
            tags.add("concentrated")
        return sorted(tags)

    def _quality_flags(self, positions: List[Dict[str, Any]], trades: List[Dict[str, Any]], errors: List[str]) -> List[str]:
        flags = []
        if errors:
            flags.append("partial_data")
        if not positions:
            flags.append("no_public_positions")
        if not trades:
            flags.append("no_public_trades")
        flags.append("trade_direction_may_be_inferred")
        return flags
