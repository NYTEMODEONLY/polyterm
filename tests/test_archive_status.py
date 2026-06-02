"""Tests for archive freshness/status reporting."""

from datetime import datetime, timedelta

from polyterm.core.archive import ArchiveCollector
from polyterm.db.database import Database
from polyterm.db.models import MarketSnapshot


def _brief(query="bitcoin", market_id="m1", slug="bitcoin-market", generated_at=None):
    return {
        "query": query,
        "market": {
            "gamma_market_id": market_id,
            "slug": slug,
            "title": "Bitcoin market",
            "condition_id": "0xabc",
        },
        "brief": {"recommendation": "research_yes"},
        "quality_flags": ["research_brief"],
        "workflow": [{"tool": "analytics.thesis", "status": "completed"}],
        "generated_at": generated_at or datetime.utcnow().isoformat() + "Z",
    }


def test_archive_status_reports_fresh_counts_and_actions(tmp_path):
    db = Database(str(tmp_path / "polyterm.db"))
    db.insert_research_brief(_brief())
    db.insert_snapshot(
        MarketSnapshot(
            market_id="m1",
            market_slug="bitcoin-market",
            title="Bitcoin market",
            probability=0.42,
            timestamp=datetime.utcnow(),
        )
    )

    status = ArchiveCollector(database=db).status(query="bitcoin", market_id="m1", max_age_hours=24)

    assert status["success"] is True
    assert status["query"] == "bitcoin"
    assert status["market_id"] == "m1"
    assert status["evidence_counts"]["research_briefs"] == 1
    assert status["evidence_counts"]["market_snapshots"] == 1
    assert status["freshness"]["research_briefs"]["status"] == "fresh"
    assert status["freshness"]["market_snapshots"]["status"] == "fresh"
    assert status["recommended_actions"] == []
    assert "archive_status" in status["quality_flags"]


def test_archive_status_marks_stale_and_missing_evidence(tmp_path):
    db = Database(str(tmp_path / "polyterm.db"))
    old = (datetime.utcnow() - timedelta(hours=72)).isoformat() + "Z"
    db.insert_research_brief(_brief(generated_at=old))

    status = ArchiveCollector(database=db).status(query="bitcoin", market_id="m1", max_age_hours=24)

    assert status["freshness"]["research_briefs"]["status"] == "stale"
    assert status["freshness"]["market_snapshots"]["status"] == "missing"
    assert "stale_research_briefs" in status["quality_flags"]
    assert "missing_market_snapshots" in status["quality_flags"]
    assert any("market.research" in action for action in status["recommended_actions"])
    assert any("collect" in action for action in status["recommended_actions"])
