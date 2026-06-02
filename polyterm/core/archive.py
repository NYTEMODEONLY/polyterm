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
