"""Archive tools for agent adapters."""

from ...contracts import envelope
from ....core.archive import ArchiveCollector
from ....db.database import Database


def search(query: str = "", limit: int = 20) -> dict:
    collector = ArchiveCollector(database=Database())
    return envelope(collector.search_research_briefs(query=query, limit=limit), meta={"tool": "archive.search"})
