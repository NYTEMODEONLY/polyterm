# PolyMarket API Setup Guide

## Overview

PolyTerm uses verified PolyMarket API endpoints that return live, current data with accurate volume information.

## ✅ Working Endpoints (October 2025)

### Gamma Markets API - `/events` endpoint
**Primary source for live data with volume**

- **URL**: `https://gamma-api.polymarket.com/events`
- **Parameters**: `active=true&closed=false`
- **Returns**: Current 2025 markets with volume data
- **Volume Fields**: `volume`, `volume24hr`
- **Status**: ✅ Working with live data

### CLOB API - `/sampling-markets` endpoint
**Fallback source for current markets (no volume)**

- **URL**: `https://clob.polymarket.com/sampling-markets`
- **Returns**: Current active markets
- **Status**: ✅ Working (fallback when Gamma fails)
- **Note**: No volume data in response

### ❌ Subgraph GraphQL (Deprecated)
**Endpoint has been removed**

- **URL**: `https://api.thegraph.com/subgraphs/name/polymarket/matic-markets`
- **Status**: ❌ Removed by The Graph (returns schema fetch error)
- **Impact**: Portfolio tracking and individual trade history unavailable
- **Workaround**: PolyTerm uses Gamma API for whale detection via volume analysis

## Data Validation

PolyTerm includes automatic data validation:

### Freshness Checks
- ✅ Rejects markets from previous years
- ✅ Validates end dates are current or future
- ✅ Filters out closed markets
- ✅ Ensures timestamps are recent

### Volume Validation
- ✅ Verifies volume data is present
- ✅ Filters markets by minimum volume threshold
- ✅ Defaults to requiring volume > $0.01

### Fallback System
- ✅ Primary: Gamma /events (has volume)
- ✅ Fallback: CLOB /sampling-markets (current markets)
- ✅ Enrichment: Subgraph (on-chain data)

## Configuration

### Default Configuration
Located in `~/.polyterm/config.toml`:

```toml
[api]
gamma_base_url = "https://gamma-api.polymarket.com"
gamma_markets_endpoint = "/events"
clob_rest_endpoint = "https://clob.polymarket.com"
clob_endpoint = "wss://ws-live-data.polymarket.com"
subgraph_endpoint = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets"

[data_validation]
max_market_age_hours = 24
require_volume_data = true
min_volume_threshold = 0.01
reject_closed_markets = true
enable_api_fallback = true
```

### Updating Configuration

```bash
# Set custom data validation
polyterm config --set data_validation.max_market_age_hours 48
polyterm config --set data_validation.min_volume_threshold 1.0

# Disable volume requirement (not recommended)
polyterm config --set data_validation.require_volume_data false
```

## Verifying Live Data

### Test Commands

```bash
# Verify you're getting current data
polyterm monitor --limit 5

# Check for 2025 markets
polyterm whales --hours 24

# Validate data freshness
python3 -m pytest tests/test_live_data/ -v
```

### Expected Results

When working correctly, you should see:
- ✅ Market questions mentioning "2025" or current events
- ✅ Volume data showing real numbers (not $0)
- ✅ "Data Age" showing current timeframes
- ✅ No markets from 2020-2024

### What You Should NOT See

- ❌ Markets from 2020-2024
- ❌ All volume showing $0.00
- ❌ Closed markets when requesting active
- ❌ "Joe Biden Coronavirus" or other historical markets

## Troubleshooting

### Issue: Getting old markets from 2020-2024

**Solution**: The app now uses `/events` endpoint automatically. If you still see old markets:

1. Check your config:
   ```bash
   polyterm config --get api.gamma_markets_endpoint
   ```
   Should return: `/events`

2. Verify API is responding:
   ```bash
   curl "https://gamma-api.polymarket.com/events?active=true&closed=false&limit=5"
   ```

3. Clear any cached data and restart

### Issue: No volume data (all $0)

**Solution**: 
1. Ensure data_validation.require_volume_data is true
2. The app automatically filters markets without volume
3. Check if you have network connectivity

```bash
polyterm config --set data_validation.require_volume_data true
```

### Issue: API rate limiting

**Solution**: 
- Built-in rate limiter handles 60 requests/minute
- Increase refresh interval if hitting limits:
  ```bash
  polyterm monitor --refresh 10  # 10 second refresh
  ```

### Issue: "No live markets found"

**Possible causes**:
1. API endpoint is down - check status.polymarket.com
2. Network connectivity issues
3. Filters too restrictive

**Solution**:
```bash
# Try with less strict filtering
polyterm config --set data_validation.min_volume_threshold 0.001
polyterm config --set data_validation.require_volume_data false
```

## Testing Live Data

### Run Integration Tests

```bash
# Full test suite
pytest tests/test_live_data/ -v

# Test data freshness only
pytest tests/test_live_data/test_live_data_freshness.py -v

# Test API endpoints
pytest tests/test_live_data/test_api_endpoints.py -v

# Critical integration test
pytest tests/test_live_data/test_integration.py::test_critical_no_old_markets_in_results -v
```

### Manual Verification

```python
from polyterm.api.gamma import GammaClient
from polyterm.api.aggregator import APIAggregator

# Test Gamma API
gamma = GammaClient()
markets = gamma.get_markets(limit=5, active=True, closed=False)

# Check for 2025 data
for market in markets:
    print(f"{market.get('question')}")
    print(f"  End date: {market.get('endDate')}")
    print(f"  24hr volume: ${market.get('volume24hr', 0):,.2f}")
    print()
```

Expected output should show 2025 markets with real volume numbers.

## API Response Format

### Gamma /events Response
```json
[
  {
    "id": "12345",
    "question": "Fed rate hike in 2025?",
    "endDate": "2025-12-10T12:00:00Z",
    "volume": 622645.28,
    "volume24hr": 1441.97,
    "active": true,
    "closed": false,
    "outcomes": "[\"Yes\", \"No\"]",
    "outcomePrices": "[\"0.42\", \"0.58\"]"
  }
]
```

## API Key (Optional)

PolyMarket's public APIs don't require authentication for read access. However, if you have an API key:

```bash
polyterm config --set api.gamma_api_key "your-api-key-here"
```

## Support

- **API Documentation**: https://docs.polymarket.com
- **API Status**: https://status.polymarket.com
- **PolyTerm Issues**: GitHub issues

## Last Updated

This guide was verified on **October 14, 2025** with confirmed working endpoints returning live 2025 data.

