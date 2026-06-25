"""Analytics tools for agent adapters."""

from ...contracts import envelope
from ....api.gamma import GammaClient
from ....api.market_utils import market_probability_price
from ....core.cross_venue import CrossVenueMonitor
from ....core.risk_score import MarketRiskScorer
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


def risk(market: str) -> dict:
    gamma = GammaClient()
    try:
        try:
            market_data = gamma.get_market(market)
        except Exception:
            results = gamma.search_markets(market, limit=5)
            market_data = results[0] if results else {}

        scorer = MarketRiskScorer()
        assessment = scorer.score_market(
            market_id=str(market_data.get("id") or market),
            title=market_data.get("question") or market_data.get("title") or market,
            description=market_data.get("description", ""),
            volume_24h=float(market_data.get("volume24hr") or market_data.get("volume24Hr") or 0),
            liquidity=float(market_data.get("liquidity") or 0),
            spread=float(market_data.get("spread") or 0),
            category=market_data.get("category", ""),
            resolution_source=market_data.get("resolutionSource", ""),
        )
        return envelope(
            {"market": market, "assessment": assessment.to_dict(), "quality_flags": ["heuristic_risk_score"]},
            meta={"tool": "analytics.risk"},
        )
    finally:
        gamma.close()
