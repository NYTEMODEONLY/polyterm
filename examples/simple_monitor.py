#!/usr/bin/env python3
"""
Simple example of using PolyTerm to monitor markets
"""

from polyterm.api.gamma import GammaClient
from polyterm.api.clob import CLOBClient
from polyterm.api.subgraph import SubgraphClient
from polyterm.core.scanner import MarketScanner
from polyterm.core.alerts import AlertManager
from polyterm.utils.config import Config


def main():
    """Simple monitoring example"""
    
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
    
    # Initialize scanner and alert manager
    scanner = MarketScanner(
        gamma_client,
        clob_client,
        subgraph_client,
        check_interval=60,
    )
    
    alert_manager = AlertManager(enable_system_notifications=False)
    
    # Define alert callback
    def on_shift(shift_data):
        print(f"\n🚨 Market Shift Detected!")
        print(f"Market: {shift_data['title']}")
        print(f"Changes: {shift_data['changes']}")
        
        # Process alerts
        thresholds = {
            "probability": 10.0,
            "volume": 50.0,
        }
        alert_manager.process_shift(shift_data, thresholds)
    
    # Add callback
    scanner.add_shift_callback(on_shift)
    
    # Get some markets to monitor
    print("Fetching active markets...")
    markets = gamma_client.get_markets(active=True, limit=10)
    market_ids = [m.get("id") for m in markets if m.get("id")]
    
    print(f"\nMonitoring {len(market_ids)} markets:")
    for market in markets[:5]:
        print(f"  - {market.get('question', 'Unknown')}")
    
    # Start monitoring
    print("\nStarting monitor... (Press Ctrl+C to stop)")
    
    try:
        scanner.start_monitoring(
            market_ids=market_ids,
            thresholds={
                "probability": 10.0,
                "volume": 50.0,
            },
        )
    except KeyboardInterrupt:
        print("\n\nStopped monitoring")
    finally:
        gamma_client.close()
        clob_client.close()


if __name__ == "__main__":
    main()

