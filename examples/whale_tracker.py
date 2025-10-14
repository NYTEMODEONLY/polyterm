#!/usr/bin/env python3
"""
Example of tracking whale trades using PolyTerm
"""

from polyterm.api.gamma import GammaClient
from polyterm.api.clob import CLOBClient
from polyterm.api.subgraph import SubgraphClient
from polyterm.core.analytics import AnalyticsEngine
from polyterm.utils.config import Config
from polyterm.utils.formatting import format_timestamp, format_volume


def main():
    """Whale tracking example"""
    
    # Load configuration
    config = Config()
    
    # Initialize API clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )
    
    subgraph_client = SubgraphClient(
        endpoint=config.subgraph_endpoint,
    )
    
    # Initialize analytics engine
    analytics = AnalyticsEngine(gamma_client, clob_client, subgraph_client)
    
    # Track whale trades
    print("🐋 Tracking Whale Trades (≥$10,000)")
    print("=" * 60)
    
    whale_trades = analytics.track_whale_trades(
        min_notional=10000,
        lookback_hours=24,
    )
    
    if not whale_trades:
        print("No whale trades found in the last 24 hours")
        return
    
    # Display whale trades
    for i, whale in enumerate(whale_trades[:10], 1):
        print(f"\n{i}. Whale Trade")
        print(f"   Trader: {whale.trader[:10]}...")
        print(f"   Market: {whale.market_id}")
        print(f"   Side: {whale.outcome}")
        print(f"   Size: {format_volume(whale.shares, use_short=False)} shares")
        print(f"   Price: ${whale.price:.4f}")
        print(f"   Notional: ${whale.notional:,.0f}")
        print(f"   Time: {format_timestamp(whale.timestamp)}")
    
    # Analyze top whale
    if whale_trades:
        top_whale = whale_trades[0]
        print(f"\n\n📊 Analyzing Top Whale: {top_whale.trader[:10]}...")
        print("=" * 60)
        
        impact = analytics.get_whale_impact_on_market(
            top_whale.market_id,
            top_whale.trader,
        )
        
        print(f"Market: {top_whale.market_id}")
        print(f"Total Trades: {impact['total_trades']}")
        print(f"Total Volume: ${impact['total_volume']:,.0f}")
        print(f"Buy Volume: ${impact['buy_volume']:,.0f}")
        print(f"Sell Volume: ${impact['sell_volume']:,.0f}")
        print(f"Net Position: ${impact['net_position']:,.0f}")
    
    # Cleanup
    gamma_client.close()
    clob_client.close()


if __name__ == "__main__":
    main()

