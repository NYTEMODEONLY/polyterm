"""Natural-language answer tool for common agentic PolyTerm queries."""

from ...contracts import envelope
from ....api.data_api import DataAPIClient
from ....core.wallet_intelligence import WalletIntelligence
from ....db.database import Database


def _classify(query: str) -> str:
    text = (query or "").lower()
    whale_terms = {"whale", "wager", "wagers", "trade", "trades", "bet", "bets"}
    top_terms = {"biggest", "largest", "top", "major"}
    if any(term in text for term in whale_terms) and any(term in text for term in top_terms):
        return "whale_wagers"
    return "unsupported"


def _confidence(quality_flags: list[str], count: int) -> str:
    if count == 0:
        return "low"
    if "data_api_page_error" in quality_flags or "data_api_recent_tape_window_limited" in quality_flags:
        return "medium"
    return "high"


def answer(query: str, hours: int = 48, limit: int = 3, min_notional: float = 10000) -> dict:
    """Answer a natural-language market-intelligence query with a tool trace.

    This intentionally starts with the high-value whale-wager path that exposed
    the prior agentic failure. Unsupported intents fail closed with a suggested
    tool route instead of fabricating an answer.
    """
    intent = _classify(query)
    if intent != "whale_wagers":
        return envelope(
            {
                "query": query,
                "intent": intent,
                "answer": "Unsupported query intent for agent.answer v1. Use agent.schemas to select a specific PolyTerm tool.",
                "confidence": "low",
                "tool_trace": ["agent.answer:intent_classifier"],
                "quality_flags": ["unsupported_intent", "fail_closed"],
            },
            meta={"tool": "agent.answer"},
        )

    data_api = DataAPIClient()
    engine = WalletIntelligence(data_api=data_api, database=Database())
    try:
        whale_result = engine.whale_trades(
            min_notional=min_notional,
            hours=hours,
            limit=limit,
            sample_size=3000,
        )
    finally:
        data_api.close()

    trades = whale_result.get("trades", [])
    lines = []
    for index, trade in enumerate(trades, start=1):
        lines.append(
            f"{index}. ${trade.get('notional', 0):,.2f} {trade.get('side') or ''} "
            f"{trade.get('outcome') or ''} — {trade.get('market_title') or trade.get('market_slug') or 'unknown market'}"
        )
    answer_text = "\n".join(lines) if lines else "No matching public whale trade rows found in the scanned window."

    quality_flags = list(whale_result.get("quality_flags", []))
    return envelope(
        {
            "query": query,
            "intent": intent,
            "answer": answer_text,
            "confidence": _confidence(quality_flags, len(trades)),
            "evidence": trades,
            "validation": {
                "rows_scanned": whale_result.get("rows_scanned"),
                "pages_scanned": whale_result.get("pages_scanned"),
                "sample_size": whale_result.get("sample_size"),
                "errors": whale_result.get("errors", []),
            },
            "tool_trace": ["agent.answer:intent_classifier", "wallet.whale_trades"],
            "quality_flags": quality_flags,
        },
        meta={"tool": "agent.answer"},
    )
