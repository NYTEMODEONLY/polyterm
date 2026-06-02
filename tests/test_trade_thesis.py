"""Tests for explainable market-level trade thesis generation."""

from datetime import datetime, timedelta

from polyterm.core.trade_thesis import TradeThesisEngine
from polyterm.db.models import MarketSnapshot, Trade


class FakeGammaClient:
    def get_market(self, identifier):
        return {
            "id": "gamma-1",
            "slug": "will-bitcoin-hit-100k",
            "question": "Will Bitcoin hit $100k?",
            "conditionId": "condition-1",
            "clobTokenIds": ["token-yes", "token-no"],
            "outcomes": ["Yes", "No"],
            "outcomePrices": ["0.72", "0.28"],
            "volume24hr": 250000,
            "liquidity": 500000,
            "active": True,
            "closed": False,
        }

    def search_markets(self, identifier, limit=5):
        return []


class FakeClobClient:
    def get_order_book(self, token_id, depth=20):
        return {
            "bids": [{"price": "0.71", "size": "1000"}],
            "asks": [{"price": "0.73", "size": "1200"}],
        }


class FakeDatabase:
    def __init__(self, trades=None, history=None):
        self.trades = trades or []
        self.history = history or []

    def get_large_trades(self, min_notional=10000, hours=72):
        cutoff = datetime.now() - timedelta(hours=hours)
        return [trade for trade in self.trades if trade.notional >= min_notional and trade.timestamp >= cutoff]

    def get_market_history(self, market_id, hours=72, limit=500):
        return self.history


def test_trade_thesis_includes_cached_whale_flow_for_resolved_market():
    db = FakeDatabase(
        trades=[
            Trade(
                market_id="condition-1",
                market_slug="will-bitcoin-hit-100k",
                wallet_address="0xaaa",
                side="BUY",
                outcome="Yes",
                price=0.72,
                size=200000,
                notional=144000,
                timestamp=datetime.now(),
                tx_hash="0x1",
            ),
            Trade(
                market_id="other-condition",
                market_slug="other-market",
                wallet_address="0xbbb",
                side="BUY",
                outcome="No",
                price=0.40,
                size=300000,
                notional=120000,
                timestamp=datetime.now(),
                tx_hash="0x2",
            ),
        ],
        history=[
            MarketSnapshot(market_id="condition-1", probability=0.70),
            MarketSnapshot(market_id="condition-1", probability=0.69),
            MarketSnapshot(market_id="condition-1", probability=0.68),
        ],
    )
    engine = TradeThesisEngine(gamma_client=FakeGammaClient(), clob_client=FakeClobClient(), database=db)

    result = engine.build("will-bitcoin-hit-100k")

    whale_flow = result["whale_flow"]
    assert whale_flow["source"] == "local_cache"
    assert whale_flow["trade_count"] == 1
    assert whale_flow["wallet_count"] == 1
    assert whale_flow["total_notional"] == 144000
    assert whale_flow["top_outcome"] == "Yes"
    assert whale_flow["trades"][0]["wallet_address"] == "0xaaa"
    assert any("Cached whale flow" in item for item in result["thesis"]["evidence"])
    assert "cached_whale_flow" in result["quality_flags"]


def test_trade_thesis_returns_structured_evidence_sources_for_agents():
    db = FakeDatabase(
        trades=[
            Trade(
                market_id="condition-1",
                market_slug="will-bitcoin-hit-100k",
                wallet_address="0xaaa",
                outcome="Yes",
                price=0.72,
                size=200000,
                notional=144000,
                timestamp=datetime.now(),
                tx_hash="0x1",
            ),
        ],
        history=[MarketSnapshot(market_id="condition-1", probability=0.70)],
    )
    engine = TradeThesisEngine(gamma_client=FakeGammaClient(), clob_client=FakeClobClient(), database=db)

    result = engine.build("will-bitcoin-hit-100k")

    sources = result["evidence_sources"]
    source_ids = {source["id"] for source in sources}
    assert {"gamma_market", "clob_orderbook", "risk_score", "local_history", "cached_whale_flow"} <= source_ids
    gamma_source = next(source for source in sources if source["id"] == "gamma_market")
    assert gamma_source["status"] == "available"
    assert gamma_source["metrics"]["probability"] == 0.72
    whale_source = next(source for source in sources if source["id"] == "cached_whale_flow")
    assert whale_source["status"] == "available"
    assert whale_source["metrics"]["trade_count"] == 1
    assert whale_source["records"][0]["tx_hash"] == "0x1"


def test_trade_thesis_labels_missing_cached_whale_flow_as_gap():
    engine = TradeThesisEngine(
        gamma_client=FakeGammaClient(),
        clob_client=FakeClobClient(),
        database=FakeDatabase(trades=[]),
    )

    result = engine.build("will-bitcoin-hit-100k")

    assert result["whale_flow"]["trade_count"] == 0
    assert "No cached whale flow for this market; run wallet.whales to enrich local evidence." in result["thesis"]["risks"]
    assert "whale_flow_unavailable" in result["quality_flags"]
