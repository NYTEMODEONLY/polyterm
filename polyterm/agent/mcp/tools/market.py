"""Market tools for agent adapters."""

from datetime import datetime, timezone

from ...contracts import envelope
from ....api.gamma import GammaClient
from ....api.market_utils import get_clob_token_ids, get_market_condition_id, market_probability_price
from ....core.market_move import MarketMoveExplainer
from ....core.market_research import MarketResearchEngine


def search(query: str, limit: int = 10) -> dict:
    gamma = GammaClient()
    try:
        markets = gamma.search_markets(query, limit=limit)
        return envelope({"query": query, "count": len(markets), "markets": markets}, meta={"tool": "market.search"})
    finally:
        gamma.close()


def resolve(identifier: str) -> dict:
    gamma = GammaClient()
    try:
        try:
            market = gamma.get_market(identifier)
        except Exception:
            results = gamma.search_markets(identifier, limit=5)
            market = next(
                (item for item in results if _is_current_market(item)),
                results[0] if results else {},
            )

        data = {
            "input": identifier,
            "market": market,
            "gamma_market_id": market.get("id"),
            "gamma_slug": market.get("slug"),
            "condition_id": get_market_condition_id(market),
            "clob_token_ids": get_clob_token_ids(market),
            "probability": market_probability_price(market),
        }
        return envelope(data, meta={"tool": "market.resolve"})
    finally:
        gamma.close()


def research(
    market: str,
    prefetch_whales: bool = False,
    min_notional: float = 100000,
    hours: int = 72,
    limit: int = 5,
    persist: bool = False,
) -> dict:
    engine = MarketResearchEngine()
    return envelope(
        engine.build(
            market,
            prefetch_whales=prefetch_whales,
            min_notional=min_notional,
            hours=hours,
            limit=limit,
            persist=persist,
        ),
        meta={"tool": "market.research"},
    )


def explain_move(market: str, hours: int = 24) -> dict:
    engine = MarketMoveExplainer()
    return envelope(engine.explain(market, hours=hours), meta={"tool": "market.explain_move"})


def _is_current_market(market):
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
