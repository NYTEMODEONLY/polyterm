"""Tests for archived market research briefs."""

from polyterm.core.archive import ArchiveCollector
from polyterm.core.market_research import MarketResearchEngine
from polyterm.db.database import Database


class FakeThesisEngine:
    def build(self, market):
        return {
            "market": {
                "gamma_market_id": "2362221",
                "slug": "bitcoin-above-66k-on-june-2-2026",
                "question": "Bitcoin above $66K on June 2?",
                "condition_id": "condition-1",
            },
            "thesis": {
                "summary": "YES has a modest edge.",
                "direction": "yes",
                "confidence": 0.66,
                "evidence": ["Evidence A"],
                "risks": ["Risk A"],
                "next_actions": ["Watch order book"],
            },
            "quality_flags": ["cached_whale_flow"],
            "evidence_sources": [
                {"id": "gamma_market", "status": "available"},
                {"id": "cached_whale_flow", "status": "available"},
            ],
        }


def test_market_research_can_persist_brief_to_archive(tmp_path):
    database = Database(str(tmp_path / "polyterm.db"))
    engine = MarketResearchEngine(thesis_engine=FakeThesisEngine(), database=database)

    result = engine.build("bitcoin", persist=True)

    assert result["archive"]["persisted"] is True
    assert result["archive"]["brief_id"] > 0

    archived = database.search_research_briefs(query="bitcoin", limit=5)
    assert len(archived) == 1
    assert archived[0]["query"] == "bitcoin"
    assert archived[0]["market_slug"] == "bitcoin-above-66k-on-june-2-2026"
    assert archived[0]["brief"]["recommendation"] == "research_yes"
    assert archived[0]["payload"]["brief"]["headline"] == "YES has a modest edge."


def test_archive_collector_searches_research_briefs(tmp_path):
    database = Database(str(tmp_path / "polyterm.db"))
    engine = MarketResearchEngine(thesis_engine=FakeThesisEngine(), database=database)
    engine.build("bitcoin", persist=True)

    collector = ArchiveCollector(database=database)
    result = collector.search_research_briefs(query="bitcoin", limit=2)

    assert result["success"] is True
    assert result["count"] == 1
    assert result["briefs"][0]["market_slug"] == "bitcoin-above-66k-on-june-2-2026"
    assert "research_brief_archive" in result["quality_flags"]
