"""Subgraph GraphQL API client for on-chain data"""

from typing import Dict, List, Optional, Any

try:
    from gql import gql, Client
    from gql.transport.requests import RequestsHTTPTransport
    HAS_GQL = True
except ImportError:
    HAS_GQL = False


class SubgraphClient:
    """Client for PolyMarket Subgraph (The Graph Protocol)"""
    
    def __init__(
        self,
        endpoint: str = "https://api.thegraph.com/subgraphs/name/polymarket/matic-markets",
    ):
        self.endpoint = endpoint
        if HAS_GQL:
            transport = RequestsHTTPTransport(url=endpoint)
            self.client = Client(transport=transport, fetch_schema_from_transport=True)
        else:
            self.client = None
    
    def query(self, query_string: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute GraphQL query
        
        Args:
            query_string: GraphQL query string
            variables: Query variables
        
        Returns:
            Query result dictionary
        """
        if not HAS_GQL or not self.client:
            raise Exception("gql package not installed. Install with: pip install gql[all]")
        try:
            query = gql(query_string)
            result = self.client.execute(query, variable_values=variables)
            return result
        except Exception as e:
            raise Exception(f"GraphQL query failed: {e}")
    
    def get_market_trades(
        self,
        market_id: str,
        first: int = 100,
        skip: int = 0,
        order_by: str = "timestamp",
        order_direction: str = "desc",
    ) -> List[Dict[str, Any]]:
        """Get trades for a market from on-chain data
        
        Args:
            market_id: Market ID
            first: Number of trades to fetch
            skip: Number of trades to skip
            order_by: Field to order by
            order_direction: 'asc' or 'desc'
        
        Returns:
            List of trade dictionaries
        """
        query_string = """
            query GetMarketTrades($marketId: String!, $first: Int!, $skip: Int!, $orderBy: String!, $orderDirection: String!) {
                trades(
                    where: { market: $marketId }
                    first: $first
                    skip: $skip
                    orderBy: $orderBy
                    orderDirection: $orderDirection
                ) {
                    id
                    trader
                    market
                    outcome
                    shares
                    price
                    timestamp
                    transactionHash
                }
            }
        """
        
        variables = {
            "marketId": market_id,
            "first": first,
            "skip": skip,
            "orderBy": order_by,
            "orderDirection": order_direction,
        }
        
        result = self.query(query_string, variables)
        return result.get("trades", [])
    
    def get_market_volume(
        self,
        market_id: str,
        start_time: Optional[int] = None,
        end_time: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Get aggregated volume for a market
        
        Args:
            market_id: Market ID
            start_time: Start timestamp (Unix)
            end_time: End timestamp (Unix)
        
        Returns:
            Volume statistics
        """
        query_string = """
            query GetMarketVolume($marketId: String!, $startTime: Int, $endTime: Int) {
                market(id: $marketId) {
                    id
                    totalVolume
                    totalLiquidity
                    trades(
                        where: {
                            timestamp_gte: $startTime
                            timestamp_lte: $endTime
                        }
                    ) {
                        shares
                        price
                    }
                }
            }
        """
        
        variables = {
            "marketId": market_id,
            "startTime": start_time,
            "endTime": end_time,
        }
        
        result = self.query(query_string, variables)
        return result.get("market", {})
    
    def get_whale_trades(
        self,
        min_notional: float = 10000,
        first: int = 100,
        skip: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get large trades (whale activity)
        
        Args:
            min_notional: Minimum trade size (shares * price)
            first: Number of trades to fetch
            skip: Number to skip
        
        Returns:
            List of large trade dictionaries
        """
        query_string = """
            query GetWhaleTrades($first: Int!, $skip: Int!) {
                trades(
                    first: $first
                    skip: $skip
                    orderBy: timestamp
                    orderDirection: desc
                ) {
                    id
                    trader
                    market
                    outcome
                    shares
                    price
                    timestamp
                    transactionHash
                }
            }
        """
        
        variables = {
            "first": first,
            "skip": skip,
        }
        
        result = self.query(query_string, variables)
        trades = result.get("trades", [])
        
        # Filter by notional value
        whale_trades = []
        for trade in trades:
            notional = float(trade["shares"]) * float(trade["price"])
            if notional >= min_notional:
                trade["notional"] = notional
                whale_trades.append(trade)
        
        return whale_trades
    
    def get_user_positions(self, wallet_address: str) -> List[Dict[str, Any]]:
        """Get positions for a wallet address
        
        Args:
            wallet_address: User's wallet address
        
        Returns:
            List of position dictionaries
        """
        query_string = """
            query GetUserPositions($walletAddress: String!) {
                positions(where: { user: $walletAddress }) {
                    id
                    user
                    market
                    outcome
                    shares
                    averagePrice
                    realizedPnL
                    unrealizedPnL
                }
            }
        """
        
        variables = {"walletAddress": wallet_address.lower()}
        
        result = self.query(query_string, variables)
        return result.get("positions", [])
    
    def get_market_liquidity_changes(
        self,
        market_id: str,
        first: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get liquidity change events for a market
        
        Args:
            market_id: Market ID
            first: Number of events to fetch
        
        Returns:
            List of liquidity event dictionaries
        """
        query_string = """
            query GetLiquidityChanges($marketId: String!, $first: Int!) {
                liquidityEvents(
                    where: { market: $marketId }
                    first: $first
                    orderBy: timestamp
                    orderDirection: desc
                ) {
                    id
                    type
                    provider
                    amount
                    timestamp
                    market
                }
            }
        """
        
        variables = {
            "marketId": market_id,
            "first": first,
        }
        
        result = self.query(query_string, variables)
        return result.get("liquidityEvents", [])
    
    def get_market_statistics(self, market_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a market
        
        Args:
            market_id: Market ID
        
        Returns:
            Market statistics dictionary
        """
        query_string = """
            query GetMarketStats($marketId: String!) {
                market(id: $marketId) {
                    id
                    question
                    totalVolume
                    totalLiquidity
                    createdAt
                    resolvedAt
                    resolved
                    outcomes
                    tradeCount
                }
            }
        """
        
        variables = {"marketId": market_id}
        
        result = self.query(query_string, variables)
        return result.get("market", {})
    
    def get_trending_markets_by_volume(
        self,
        time_window: int = 86400,  # 24 hours
        first: int = 10,
    ) -> List[Dict[str, Any]]:
        """Get trending markets by recent volume
        
        Args:
            time_window: Time window in seconds
            first: Number of markets to return
        
        Returns:
            List of trending market dictionaries
        """
        import time
        end_time = int(time.time())
        start_time = end_time - time_window
        
        query_string = """
            query GetTrendingMarkets($startTime: Int!, $first: Int!) {
                markets(
                    first: $first
                    orderBy: totalVolume
                    orderDirection: desc
                    where: { createdAt_gte: $startTime }
                ) {
                    id
                    question
                    totalVolume
                    totalLiquidity
                    tradeCount
                    outcomes
                }
            }
        """
        
        variables = {
            "startTime": start_time,
            "first": first,
        }
        
        result = self.query(query_string, variables)
        return result.get("markets", [])

