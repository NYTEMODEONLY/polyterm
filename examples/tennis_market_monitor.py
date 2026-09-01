#!/usr/bin/env python3
"""
Overlay live tennis match state onto a Polymarket tennis event.

This mirrors examples/simple_monitor.py: PolyTerm's own GammaClient is the sole
source of Polymarket market data, and this script adds a read-only, independent
live-score/status overlay next to it. It places no orders and imports no
execution code.

Vendor disclosure: the live match-state feed used here is the Live Tennis API
(https://livetennisapi.com), which I run — so this example is vendor-authored;
judge accordingly. It is used only as an external annotation on PolyTerm's
Polymarket data, never as an oracle, venue, or resolution source. Always confirm
a market's official resolution criteria on its Polymarket page.

The free keyed tier (https://livetennisapi.com/subscribe/free) returns live
matches, scores, server and break-point state at 30 req/min and 100 req/day —
enough for a develop-and-test or ~15-minute-cadence check, not continuous fast
polling. Export LIVETENNIS_API_KEY to enable the overlay; without it the script
still prints the Polymarket side and skips the tennis annotation.

    export LIVETENNIS_API_KEY="your-free-key"
    python examples/tennis_market_monitor.py            # searches "tennis"
    python examples/tennis_market_monitor.py <slug|id>  # a specific market
"""

import os
import sys
from typing import Any, Dict, List, Optional

import requests

from polyterm.api.gamma import GammaClient
from polyterm.api.market_utils import market_probability_price, parse_list_field
from polyterm.utils.config import Config

LIVE_TENNIS_BASE_URL = "https://api.livetennisapi.com/api/public/v1"


class LiveTennisClient:
    """Minimal read-only Live Tennis API client (free-tier endpoints only).

    Only the FREE endpoints are used: `GET /matches?status=live` and each
    match's embedded score. See https://docs.livetennisapi.com for the full
    surface (history, market prices and win-probability are paid tiers).
    """

    def __init__(self, api_key: str, base_url: str = LIVE_TENNIS_BASE_URL):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-API-Key": api_key})

    def get_live_matches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Return live matches (FREE `status=live`), each with its latest score."""
        resp = self.session.get(
            f"{self.base_url}/matches",
            params={"status": "live", "limit": limit},
            timeout=15,
        )
        resp.raise_for_status()
        payload = resp.json()
        return payload.get("data", []) if isinstance(payload, dict) else []

    def close(self) -> None:
        self.session.close()


def derive_break_point(score: Dict[str, Any]) -> Optional[int]:
    """Which player (1 or 2) is holding a break point, or None.

    Break point per the Live Tennis API convention: the RECEIVER is at AD, or
    the receiver is at 40 while the server is at 0/15/30. Never in a tiebreak,
    and never when server or points are null.
    """
    if not score or score.get("is_tiebreak"):
        return None

    server = score.get("server")
    if server not in (1, 2):
        return None

    points = score.get("points") or []
    if len(points) < 2:
        return None

    receiver = 2 if server == 1 else 1
    server_point = points[server - 1]
    receiver_point = points[receiver - 1]
    if server_point is None or receiver_point is None:
        return None

    if receiver_point == "AD":
        return receiver
    if receiver_point == "40" and server_point in ("0", "15", "30"):
        return receiver
    return None


def format_score(score: Optional[Dict[str, Any]]) -> str:
    """Compact one-line score summary from the free score payload."""
    if not score:
        return "no score yet"
    sets = score.get("sets") or []
    points = score.get("points") or []
    parts = []
    if sets:
        parts.append("sets " + "-".join(str(s) for s in sets))
    if points and any(p is not None for p in points):
        parts.append("pts " + "-".join(str(p) if p is not None else "?" for p in points))
    if score.get("is_tiebreak"):
        parts.append("(tiebreak)")
    return ", ".join(parts) if parts else "in progress"


def match_players(live_match: Dict[str, Any]) -> List[str]:
    """Lowercase surnames of a live match's two participants, for name matching."""
    players = live_match.get("players") or {}
    names = []
    for key in ("p1", "p2"):
        name = (players.get(key) or {}).get("name")
        if name:
            names.append(name.split()[-1].lower())
    return names


def find_live_overlay(
    question: str, live_matches: List[Dict[str, Any]]
) -> Optional[Dict[str, Any]]:
    """Best-effort: the live match whose BOTH surnames appear in the question."""
    q = question.lower()
    for live_match in live_matches:
        surnames = match_players(live_match)
        if len(surnames) == 2 and all(s in q for s in surnames):
            return live_match
    return None


def main():
    """Monitor Polymarket tennis events with an independent live-state overlay."""
    config = Config()
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    # Optional Live Tennis overlay — only when a free key is present.
    tennis_client = None
    live_matches: List[Dict[str, Any]] = []
    api_key = os.environ.get("LIVETENNIS_API_KEY", "").strip()
    if api_key:
        tennis_client = LiveTennisClient(api_key)
        try:
            live_matches = tennis_client.get_live_matches()
            print(f"Live Tennis API: {len(live_matches)} match(es) in progress\n")
        except requests.RequestException as exc:
            print(f"Live Tennis overlay unavailable ({exc}); showing markets only\n")
    else:
        print(
            "LIVETENNIS_API_KEY not set — showing Polymarket data only. Get a free "
            "key at https://livetennisapi.com/subscribe/free\n"
        )

    # Resolve which Polymarket tennis market(s) to show.
    arg = sys.argv[1] if len(sys.argv) > 1 else None
    if arg:
        print(f"Fetching Polymarket market: {arg}")
        market = gamma_client.get_market(arg)
        markets = [market] if market else []
    else:
        print("Searching Polymarket for tennis markets...")
        markets = gamma_client.search_markets("tennis", limit=10)

    if not markets:
        print("No matching Polymarket markets found.")
        gamma_client.close()
        if tennis_client:
            tennis_client.close()
        return

    print(f"\nShowing {len(markets)} market(s):\n" + "=" * 60)
    for market in markets:
        question = market.get("question", market.get("title", "Unknown"))
        price = market_probability_price(market)
        outcomes = parse_list_field(market.get("outcomes"))
        outcome_prices = parse_list_field(market.get("outcomePrices"))

        print(f"\n{question}")
        print(f"  YES price / implied prob: {price:.2%}")
        if outcomes and outcome_prices:
            for name, op in zip(outcomes, outcome_prices):
                try:
                    print(f"    {name}: {float(op):.2%}")
                except (TypeError, ValueError):
                    print(f"    {name}: {op}")

        # Overlay independent live match state, when we can match it by name.
        if live_matches:
            live = find_live_overlay(str(question), live_matches)
            if live:
                score = live.get("score")
                print(f"  Live state: {format_score(score)}")
                server = (score or {}).get("server")
                if server in (1, 2):
                    players = live.get("players") or {}
                    server_name = (players.get(f"p{server}") or {}).get("name", f"P{server}")
                    print(f"  Serving: {server_name}")
                bp = derive_break_point(score or {})
                if bp:
                    players = live.get("players") or {}
                    bp_name = (players.get(f"p{bp}") or {}).get("name", f"P{bp}")
                    print(f"  ⚡ Break point for {bp_name}")
                status = live.get("event_status")
                if status:
                    print(f"  Match note: {status}")
            else:
                print("  Live state: no in-progress match matched by name")

    gamma_client.close()
    if tennis_client:
        tennis_client.close()


if __name__ == "__main__":
    main()
