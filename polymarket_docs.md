# Polymarket Documentation Guide 📊

A comprehensive guide to Polymarket's core concepts, terminology, and API structure for developers using PolyTerm.

## Table of Contents

- [Introduction](#introduction)
- [Core Terminology](#core-terminology)
- [API Architecture Overview](#api-architecture-overview)
- [Key Concepts for Developers](#key-concepts-for-developers)
- [Integration with PolyTerm](#integration-with-polyterm)
- [Additional Resources](#additional-resources)

## Introduction

Polymarket is a decentralized prediction market platform built on Ethereum and Polygon that allows users to trade on the outcomes of future events. Users can buy and sell tokens representing different outcomes, with prices reflecting the market's collective belief about the probability of each outcome.

**Official Documentation**: [Polymarket Developer Docs](https://docs.polymarket.com/quickstart/introduction/definitions)

## Core Terminology

| Term | Definition |
|------|------------|
| **Token** | A token represents a stake in a specific Yes/No outcome in a Market. The price of a token can fluctuate between 0−1 based on the market belief in the outcome. When a market resolves, the token associated with the correct prediction can be redeemed for $1 USDC. This is also sometimes called an _Asset Id_ |
| **Market** | A single event outcome. Corresponds to a pair of CLOB token IDs(Yes/No), a market address, a question ID and a condition ID. |
| **Event** | A collection of related markets grouped under a common topic or theme. |
| **SLUG** | A human readable identification for a market or event. Can be found in the URL of any Polymarket Market or Event. You can use this slug to find more detailed information about a market or event by using it as a parameter in the [Get Events](https://docs.polymarket.com/developers/gamma-markets-api/get-events) or [Get Markets](https://docs.polymarket.com/developers/gamma-markets-api/get-markets) endpoints. |
| **Negative Risk (negrisk)** | A group of Markets(Event) in which only one Market can resolve as yes. For more detail see [Negrisk Details](https://docs.polymarket.com/developers/neg-risk/overview) |
| **Central Limit Order Book** | The off-chain order matching system. This is where you place resting orders and market orders are matched with existing orders before being sent on-chain. |
| **Polygon Network** | A scalable, multi-chain blockchain platform used by Polymarket to facilitate on-chain activities(contract creation, token transfers, etc) |

## API Architecture Overview

PolyTerm integrates with Polymarket's multi-layered API architecture:

### Gamma API
- **Purpose**: Primary source for market data and metadata
- **Endpoint**: `https://gamma-api.polymarket.com`
- **Key Endpoints**:
  - `/events` - Market events and data
  - `/markets` - Individual market information
  - `/series` - Market series data
- **Data Includes**: Market questions, probabilities, volume, end dates

### CLOB (Central Limit Order Book) API
- **Purpose**: Order book data and trading information
- **Endpoint**: `https://clob.polymarket.com`
- **Key Endpoints**:
  - `/sampling-markets` - Current active markets
  - `/orderbook` - Order book data
  - `/pricing` - Current pricing information
- **Data Includes**: Order book depth, spreads, current prices

### Subgraph (Deprecated)
- **Status**: ❌ Removed by The Graph
- **Previous Purpose**: On-chain data and historical trades
- **Impact**: Portfolio tracking and individual trade history unavailable
- **Workaround**: PolyTerm uses volume analysis for whale detection

## Key Concepts for Developers

### Market Structure

Each Polymarket prediction market consists of:

1. **Market Question**: The event being predicted (e.g., "Will Bitcoin reach $100k in 2025?")
2. **Token Pair**: Yes/No tokens representing opposite outcomes
3. **Probability**: Current market probability (0-100%)
4. **Volume**: Trading activity (24hr volume, total volume)
5. **End Date**: When the market resolves
6. **Resolution**: How the outcome is determined

### Token Pricing Mechanics

- **Price Range**: Tokens trade between $0.00 and $1.00
- **Probability**: Token price directly reflects market probability
  - $0.50 token = 50% probability
  - $0.75 token = 75% probability
- **Resolution**: Winning tokens redeem for $1.00 USDC
- **Liquidity**: Higher volume markets have tighter spreads

### Event Grouping

Events organize related markets:

```json
{
  "event": "2025 Presidential Election",
  "markets": [
    "Will Trump win?",
    "Will Biden win?", 
    "Will Harris win?",
    "Will DeSantis win?"
  ]
}
```

### Negative Risk Markets

Special event type where only one outcome can be true:

- **Example**: "Who will win the 2025 election?"
- **Constraint**: Only one candidate can win
- **Risk Management**: Prevents over-exposure to correlated outcomes

## Integration with PolyTerm

PolyTerm leverages Polymarket's API architecture to provide real-time market monitoring:

### Data Flow

1. **Primary Source**: Gamma API `/events` endpoint
2. **Fallback**: CLOB API `/sampling-markets` 
3. **Enrichment**: Volume analysis for whale detection
4. **Validation**: Freshness checks and data filtering

### Key Features

| Feature | Data Source | Description |
|---------|-------------|-------------|
| **Market Monitoring** | Gamma API | Real-time probability tracking |
| **Whale Detection** | Volume Analysis | High-volume market identification |
| **Market Watching** | CLOB API | Specific market alerts |
| **Data Export** | Gamma API | JSON/CSV export capabilities |

### Configuration

PolyTerm's configuration aligns with Polymarket's API structure:

```toml
[api]
gamma_base_url = "https://gamma-api.polymarket.com"
gamma_markets_endpoint = "/events"
clob_rest_endpoint = "https://clob.polymarket.com"
clob_endpoint = "wss://ws-live-data.polymarket.com"

[data_validation]
max_market_age_hours = 24
require_volume_data = true
min_volume_threshold = 0.01
reject_closed_markets = true
```

## Additional Resources

### Official Polymarket Documentation
- [Developer Quickstart](https://docs.polymarket.com/quickstart/introduction/definitions)
- [CLOB API Reference](https://docs.polymarket.com/developers/clob/introduction)
- [Gamma Markets API](https://docs.polymarket.com/developers/gamma-markets-api/overview)
- [WebSocket Documentation](https://docs.polymarket.com/developers/websocket/overview)

### PolyTerm Documentation
- **[README.md](README.md)** - Project overview and installation
- **[API_SETUP.md](API_SETUP.md)** - Technical API configuration
- **[TUI_GUIDE.md](TUI_GUIDE.md)** - Terminal user interface guide
- **[CONTRIBUTING.md](CONTRIBUTING.md)** - Development guidelines

### External Resources
- [Polymarket Status Page](https://status.polymarket.com)
- [Polygon Network Documentation](https://docs.polygon.technology/)
- [The Graph Protocol](https://thegraph.com/docs/)

### Community
- [Polymarket Discord](https://discord.gg/polymarket)
- [Polymarket Twitter](https://twitter.com/polymarket)
- [PolyTerm GitHub Issues](https://github.com/NYTEMODEONLY/polyterm/issues)

---

**Last Updated**: October 2025  
**PolyTerm Version**: v0.1.5  
**Polymarket API Status**: Live and verified

*This guide provides the foundation for understanding Polymarket's architecture when using PolyTerm for prediction market analysis.*
