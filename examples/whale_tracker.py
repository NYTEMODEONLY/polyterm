#!/usr/bin/env python3
"""
Example: high-volume market heuristic vs wallet-level whale trades.

`detect_high_volume_markets` uses Gamma 24h volume. It does not identify
traders. Use `WalletIntelligence.live_whales` for public Data API trades
with wallet addresses.
"""

from polyterm.api.gamma import GammaClient
from polyterm.core.volume_spikes import detect_high_volume_markets
from polyterm.utils.config import Config
from polyterm.utils.formatting import format_volume


def main():
    config = Config()
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )

    print("High-volume markets (Gamma 24h volume heuristic, not whale identity)")
    print("=" * 60)

    markets = detect_high_volume_markets(gamma_client, min_volume=10000)

    if not markets:
        print("No high-volume markets found")
        gamma_client.close()
        return

    for i, market in enumerate(markets[:10], 1):
        print(f"\n{i}. {market.market_title}")
        print(f"   Market ID: {market.market_id}")
        print(f"   Outcome lean: {market.outcome_lean}")
        print(f"   Last price: ${market.last_price:.4f}")
        print(f"   24h volume: ${format_volume(market.volume_24hr, use_short=False)}")
        print(f"   Evidence: {market.evidence_level}")

    print("\nFor wallet-level whale trades: polyterm whales --wallets")
    gamma_client.close()


if __name__ == "__main__":
    main()
