"""Analytics tools for agent adapters."""

from ...contracts import envelope
from ....api.gamma import GammaClient
from ....core.cross_venue import CrossVenueMonitor
from ....core.trade_thesis import TradeThesisEngine
from ....db.database import Database


def arbitrage(min_spread: float = 0.025, venues: str = "polymarket") -> dict:
    monitor = CrossVenueMonitor()
    return envelope(
        monitor.scan(query="", min_spread=min_spread, venues=venues.split(",")),
        meta={"tool": "analytics.arbitrage"},
    )


def thesis(market: str) -> dict:
    gamma = GammaClient()
    try:
        engine = TradeThesisEngine(gamma_client=gamma, database=Database())
        return envelope(engine.build(market), meta={"tool": "analytics.thesis"})
    finally:
        gamma.close()
