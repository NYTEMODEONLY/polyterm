"""Research archive collection and dataset export helpers."""

import csv
import io
import json
import time
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

from ..api.gamma import GammaClient
from ..api.market_utils import market_probability_price
from ..db.database import Database
from ..db.models import MarketSnapshot


class ArchiveCollector:
    """Collect repeatable market snapshots into the local database."""

    def __init__(self, database: Optional[Database] = None, gamma_client: Optional[GammaClient] = None):
        self.db = database or Database()
        self.gamma = gamma_client or GammaClient()

    def collect_once(self, market: str) -> Dict[str, Any]:
        """Collect one market snapshot."""
        market_data = self._resolve_market(market)
        if not market_data:
            return {
                "success": False,
                "market": market,
                "snapshot_id": None,
                "quality_flags": ["market_not_found"],
            }

        snapshot = MarketSnapshot(
            market_id=str(market_data.get("id") or market_data.get("conditionId") or market),
            market_slug=market_data.get("slug") or "",
            title=market_data.get("question") or market_data.get("title") or "",
            probability=market_probability_price(market_data),
            volume_24h=float(market_data.get("volume24hr") or market_data.get("volume24Hr") or 0),
            liquidity=float(market_data.get("liquidity") or 0),
            best_bid=float(market_data.get("bestBid") or 0),
            best_ask=float(market_data.get("bestAsk") or 0),
            spread=float(market_data.get("spread") or 0),
            timestamp=datetime.now(),
        )
        snapshot_id = self.db.insert_snapshot(snapshot)
        return {
            "success": True,
            "snapshot_id": snapshot_id,
            "market_id": snapshot.market_id,
            "title": snapshot.title,
            "probability": snapshot.probability,
            "quality_flags": self._quality_flags(market_data),
        }

    def collect_for_duration(self, market: str, interval_seconds: int, duration_seconds: int) -> Dict[str, Any]:
        """Collect snapshots for a foreground duration."""
        started = time.time()
        snapshots = []
        while time.time() - started <= duration_seconds:
            snapshots.append(self.collect_once(market))
            if time.time() - started >= duration_seconds:
                break
            time.sleep(max(interval_seconds, 1))
        return {
            "market": market,
            "interval_seconds": interval_seconds,
            "duration_seconds": duration_seconds,
            "snapshot_count": len([s for s in snapshots if s.get("success")]),
            "snapshots": snapshots,
            "quality_flags": sorted({flag for s in snapshots for flag in s.get("quality_flags", [])}),
        }

    def dataset_manifest(self, dataset: str = "latest") -> Dict[str, Any]:
        """Return a local dataset manifest without reading private data."""
        stats = self.db.get_database_stats()
        latest_snapshots = self.db.get_recent_snapshots(limit=25)
        return {
            "dataset": dataset,
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "tables": stats,
            "latest_snapshots": latest_snapshots,
            "quality_flags": ["local_sqlite_dataset", "read_only_export"],
        }

    def export_dataset(self, dataset: str = "latest", output_format: str = "json") -> str:
        """Export a dataset manifest as JSON or CSV."""
        manifest = self.dataset_manifest(dataset)
        if output_format == "json":
            return json.dumps(manifest, indent=2, default=str)
        if output_format == "csv":
            return self._manifest_csv(manifest)
        raise ValueError(f"Unsupported dataset export format: {output_format}")

    def search_research_briefs(self, query: str = "", limit: int = 20) -> Dict[str, Any]:
        """Search archived agent-native research briefs."""
        briefs = self.db.search_research_briefs(query=query, limit=limit)
        return {
            "success": True,
            "query": query,
            "count": len(briefs),
            "briefs": briefs,
            "quality_flags": ["research_brief_archive", "local_sqlite_dataset", "read_only_export"],
        }

    def status(self, query: str = "", market_id: str = "", max_age_hours: int = 24) -> Dict[str, Any]:
        """Return local archive coverage and freshness for a market/query."""
        briefs = self.db.search_research_briefs(query=query or market_id, limit=100)
        inferred_market_id = market_id or _first_nonempty([b.get("market_id") for b in briefs])
        snapshots = self.db.get_market_history(inferred_market_id, hours=24 * 365 * 10, limit=1000) if inferred_market_id else []
        orderbook_snapshots = self.db.get_evidence_snapshots("orderbook", inferred_market_id, limit=1000) if inferred_market_id else []
        price_history_snapshots = self.db.get_evidence_snapshots("price_history", inferred_market_id, limit=1000) if inferred_market_id else []
        latest_brief = briefs[0] if briefs else None
        latest_snapshot = snapshots[0] if snapshots else None
        latest_orderbook = orderbook_snapshots[0] if orderbook_snapshots else None
        latest_price_history = price_history_snapshots[0] if price_history_snapshots else None

        freshness = {
            "research_briefs": self._freshness(latest_brief.get("generated_at") if latest_brief else None, max_age_hours),
            "market_snapshots": self._freshness(latest_snapshot.timestamp.isoformat() if latest_snapshot else None, max_age_hours),
            "orderbook_snapshots": self._freshness(
                latest_orderbook.get("captured_at") if latest_orderbook else None, max_age_hours
            ),
            "price_history_snapshots": self._freshness(
                latest_price_history.get("captured_at") if latest_price_history else None, max_age_hours
            ),
        }
        quality_flags = ["archive_status", "local_sqlite_dataset", "read_only_export"]
        recommended_actions = []

        if freshness["research_briefs"]["status"] == "stale":
            quality_flags.append("stale_research_briefs")
            recommended_actions.append("Run market.research with persist=true to refresh the archived research brief.")
        elif freshness["research_briefs"]["status"] == "missing":
            quality_flags.append("missing_research_briefs")
            recommended_actions.append("Run market.research with persist=true to create an archived research brief.")

        if freshness["market_snapshots"]["status"] == "stale":
            quality_flags.append("stale_market_snapshots")
            recommended_actions.append("Run market.research with persist=true to refresh local market snapshots.")
        elif freshness["market_snapshots"]["status"] == "missing":
            quality_flags.append("missing_market_snapshots")
            recommended_actions.append("Run market.research with persist=true to create local market snapshots.")

        for key, label in [
            ("orderbook_snapshots", "order book"),
            ("price_history_snapshots", "price history"),
        ]:
            status = freshness[key]["status"]
            if status == "stale":
                quality_flags.append(f"stale_{key}")
                recommended_actions.append(f"Run market.research with persist=true to refresh local {label} snapshots.")
            elif status == "missing":
                quality_flags.append(f"missing_{key}")
                recommended_actions.append(f"Run market.research with persist=true to create local {label} snapshots.")

        return {
            "success": True,
            "query": query,
            "market_id": inferred_market_id or market_id,
            "max_age_hours": max_age_hours,
            "evidence_counts": {
                "research_briefs": len(briefs),
                "market_snapshots": len(snapshots),
                "orderbook_snapshots": len(orderbook_snapshots),
                "price_history_snapshots": len(price_history_snapshots),
            },
            "freshness": freshness,
            "latest": {
                "research_brief": latest_brief,
                "market_snapshot": latest_snapshot.to_dict() if latest_snapshot else None,
                "orderbook_snapshot": latest_orderbook,
                "price_history_snapshot": latest_price_history,
            },
            "recommended_actions": recommended_actions,
            "quality_flags": quality_flags,
        }

    def _freshness(self, timestamp: Optional[str], max_age_hours: int) -> Dict[str, Any]:
        if not timestamp:
            return {"status": "missing", "timestamp": None, "age_hours": None, "max_age_hours": max_age_hours}
        parsed = _parse_datetime(timestamp)
        age_hours = (datetime.now(timezone.utc) - parsed).total_seconds() / 3600
        return {
            "status": "fresh" if age_hours <= max_age_hours else "stale",
            "timestamp": timestamp,
            "age_hours": round(age_hours, 3),
            "max_age_hours": max_age_hours,
        }

    def _resolve_market(self, market: str) -> Dict[str, Any]:
        try:
            data = self.gamma.get_market(market)
            if data:
                return data
        except Exception:
            pass
        results = self.gamma.search_markets(market, limit=5)
        for item in results:
            if _is_current_market(item):
                return item
        return results[0] if results else {}

    def _quality_flags(self, market_data: Dict[str, Any]) -> List[str]:
        flags = []
        if not market_data.get("clobTokenIds"):
            flags.append("missing_token_ids")
        if not market_data.get("volume24hr") and not market_data.get("volume24Hr"):
            flags.append("missing_24h_volume")
        return flags or ["live_gamma_snapshot"]

    def _manifest_csv(self, manifest: Dict[str, Any]) -> str:
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=["table", "rows"])
        writer.writeheader()
        for table, rows in manifest.get("tables", {}).items():
            writer.writerow({"table": table, "rows": rows})
        return buffer.getvalue()


def _first_nonempty(values: Iterable[Any]) -> str:
    for value in values:
        if value:
            return str(value)
    return ""


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _is_current_market(market: Dict[str, Any]) -> bool:
    if not market.get("active", True) or market.get("closed", False):
        return False
    end_date = market.get("endDate") or market.get("end_date_iso")
    if not end_date:
        return True
    try:
        parsed = datetime.fromisoformat(str(end_date).replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed > datetime.now(timezone.utc)
    except Exception:
        return True
