"""Monitor command - real-time market feed"""

import click
import json
import time
from rich.console import Console
from rich.table import Table
from rich.live import Live

from ...api.gamma import GammaClient
from ...api.clob import CLOBClient
from ...api.subgraph import SubgraphClient
from ...api.aggregator import APIAggregator
from ...core.scanner import MarketScanner
from ...utils.formatting import format_probability_rich, format_volume
from ...utils.json_output import print_json, format_markets_json
from ...utils.errors import handle_api_error, show_error
from ...core.wash_trade_detector import quick_wash_trade_score
from datetime import datetime

try:
    from dateutil import parser as date_parser
    HAS_DATEUTIL = True
except ImportError:
    HAS_DATEUTIL = False


# Category keywords for filtering (since API doesn't provide category field)
# Main categories and sub-categories for granular filtering
CATEGORY_KEYWORDS = {
    # Main sports category
    'sports': ['nfl', 'nba', 'mlb', 'nhl', 'super bowl', 'world series', 'playoffs',
               'championship', 'soccer', 'football', 'baseball', 'basketball', 'hockey',
               'tennis', 'golf', 'ufc', 'boxing', 'f1', 'formula 1', 'olympics', 'fifa',
               'premier league', 'world cup', 'mvp', 'coach', 'draft pick', 'trade deadline',
               'stanley cup', 'masters', 'pga', 'wimbledon', 'us open'],

    # Sports sub-categories
    'nfl': ['nfl', 'super bowl', 'afc', 'nfc', 'touchdown', 'quarterback', 'patriots',
            'chiefs', 'eagles', 'cowboys', 'packers', 'ravens', 'bills', 'dolphins',
            'broncos', 'seahawks', 'rams', '49ers', 'lions', 'bears', 'jets', 'giants',
            'steelers', 'bengals', 'browns', 'texans', 'colts', 'jaguars', 'titans',
            'raiders', 'chargers', 'cardinals', 'falcons', 'panthers', 'saints', 'buccaneers',
            'vikings', 'commanders', 'football'],
    'nba': ['nba', 'basketball', 'lakers', 'celtics', 'warriors', 'nets', 'bucks',
            'heat', 'suns', 'nuggets', 'clippers', 'knicks', 'mavericks', 'grizzlies',
            'playoffs', 'finals', 'mvp', 'all-star'],
    'mlb': ['mlb', 'baseball', 'world series', 'yankees', 'dodgers', 'red sox', 'cubs',
            'mets', 'braves', 'astros', 'phillies', 'padres', 'mariners'],
    'nhl': ['nhl', 'hockey', 'stanley cup', 'bruins', 'rangers', 'maple leafs', 'canadiens',
            'penguins', 'blackhawks', 'oilers', 'avalanche', 'lightning', 'panthers'],
    'soccer': ['soccer', 'football', 'premier league', 'world cup', 'fifa', 'champions league',
               'manchester', 'liverpool', 'chelsea', 'arsenal', 'barcelona', 'real madrid',
               'messi', 'ronaldo', 'la liga', 'bundesliga', 'serie a'],
    'golf': ['golf', 'pga', 'masters', 'us open', 'british open', 'ryder cup', 'tour'],
    'tennis': ['tennis', 'wimbledon', 'us open', 'french open', 'australian open',
               'grand slam', 'atp', 'wta'],
    'ufc': ['ufc', 'mma', 'boxing', 'fight', 'knockout', 'heavyweight', 'lightweight'],
    'f1': ['f1', 'formula 1', 'formula one', 'grand prix', 'nascar', 'racing', 'indy'],

    # Main crypto category
    'crypto': ['bitcoin', 'btc ', ' btc', 'ethereum', ' eth ', ' eth?', 'solana', ' sol ',
               ' xrp', 'crypto', 'blockchain', 'defi', ' nft', 'coinbase', 'binance', 'satoshi'],

    # Crypto sub-categories
    'bitcoin': ['bitcoin', 'btc ', ' btc', 'satoshi', 'btc etf', 'bitcoin etf'],
    'ethereum': ['ethereum', ' eth ', ' eth?', ' eth ', 'vitalik', 'eth etf'],
    'solana': ['solana', ' sol '],
    'altcoins': [' xrp', 'ripple', 'cardano', ' ada', 'polkadot', 'avalanche', 'chainlink',
                 'dogecoin', 'shiba', 'polygon', 'matic'],

    # Main politics category
    'politics': ['trump', 'biden', 'president', 'election', 'congress', 'senate', 'house of rep',
                 'republican', 'democrat', 'governor', 'mayor', 'cabinet', 'veto',
                 'impeach', 'scotus', 'supreme court', 'primary', 'nominee'],

    # Politics sub-categories
    'trump': ['trump', 'donald', 'maga', 'mar-a-lago'],
    'elections': ['election', 'vote', 'ballot', 'primary', 'nominee', 'electoral', 'swing state'],
    'congress': ['congress', 'senate', 'house of rep', 'speaker', 'filibuster', 'bill pass'],
}


def matches_category(market: dict, category: str) -> bool:
    """Check if market matches a category using keyword search"""
    import re

    if not category:
        return True

    category_lower = category.lower()

    # First check if API provides category field
    market_category = market.get('category')
    if market_category and category_lower in market_category.lower():
        return True

    # Search in question/title - add spaces for word boundary matching
    title = ' ' + market.get('question', market.get('title', '')).lower() + ' '

    # If category is a predefined one, use keywords
    if category_lower in CATEGORY_KEYWORDS:
        for kw in CATEGORY_KEYWORDS[category_lower]:
            # For short keywords (3 chars or less), use word boundary matching
            if len(kw.strip()) <= 3:
                # Use regex word boundary for short keywords
                pattern = r'\b' + re.escape(kw.strip()) + r'\b'
                if re.search(pattern, title):
                    return True
            else:
                if kw in title:
                    return True
        return False

    # Otherwise, do a direct search
    return category_lower in title


@click.command()
@click.option("--limit", default=20, help="Maximum number of markets to display")
@click.option("--category", default=None, help="Filter by category (politics, crypto, sports)")
@click.option("--refresh", default=5, help="Refresh interval in seconds")
@click.option("--active-only", is_flag=True, help="Show only active markets")
@click.option("--sort", type=click.Choice(["volume", "probability", "recent"]), default=None, help="Sort markets by: volume, probability, or recent")
@click.option("--format", "output_format", type=click.Choice(["table", "json"]), default="table", help="Output format: table (default) or json")
@click.option("--once", is_flag=True, help="Run once and exit (no live updates)")
@click.option("--show-quality", is_flag=True, help="Show volume quality indicators (wash trade detection)")
@click.pass_context
def monitor(ctx, limit, category, refresh, active_only, sort, output_format, once, show_quality):
    """Monitor markets in real-time with live updates"""
    
    config = ctx.obj["config"]
    console = Console()
    
    # Initialize clients
    gamma_client = GammaClient(
        base_url=config.gamma_base_url,
        api_key=config.gamma_api_key,
    )
    clob_client = CLOBClient(
        rest_endpoint=config.clob_rest_endpoint,
        ws_endpoint=config.clob_endpoint,
    )
    subgraph_client = SubgraphClient(endpoint=config.subgraph_endpoint)
    
    # Initialize aggregator for live data
    aggregator = APIAggregator(gamma_client, clob_client, subgraph_client)
    
    # Initialize scanner
    scanner = MarketScanner(
        gamma_client,
        clob_client,
        subgraph_client,
        check_interval=refresh,
    )
    
    def generate_table():
        """Generate market table"""
        now = datetime.now()
        table = Table(title=f"PolyTerm - Live Market Monitor (Updated: {now.strftime('%H:%M:%S')})")
        
        table.add_column("Market", style="cyan", no_wrap=False, max_width=40 if show_quality else 45)
        table.add_column("Prob", justify="right", style="green")
        table.add_column("24h Volume", justify="right", style="yellow")
        if show_quality:
            table.add_column("Quality", justify="center", width=7)
        table.add_column("Ends", justify="right", style="dim")
        
        try:
            # When filtering by category, fetch many more markets since we filter after
            # Need at least 100 to find enough category-specific markets
            fetch_limit = max(100, limit * 10) if category else limit

            # Get live markets from aggregator with validation
            if sort == 'volume':
                # Use dedicated method for volume-sorted markets
                markets = aggregator.get_top_markets_by_volume(limit=fetch_limit, min_volume=0.01)
            else:
                markets = aggregator.get_live_markets(
                    limit=fetch_limit,
                    require_volume=True,
                    min_volume=0.01
                )

            # Filter by category if specified (uses keyword matching)
            if category:
                markets = [m for m in markets if matches_category(m, category)]
                markets = markets[:limit]  # Apply limit after filtering

            # Filter by active status
            if active_only:
                markets = [m for m in markets if m.get('active', False) and not m.get('closed', True)]

            # Apply additional sorting if specified
            if sort == 'probability':
                def get_probability(m):
                    outcome_prices = m.get('outcomePrices')
                    if not outcome_prices and m.get('markets') and len(m.get('markets', [])) > 0:
                        outcome_prices = m['markets'][0].get('outcomePrices')
                    if isinstance(outcome_prices, str):
                        import json
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except Exception:
                            return 0
                    if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                        return float(outcome_prices[0])
                    return 0
                markets = sorted(markets, key=get_probability, reverse=True)
            elif sort == 'recent':
                markets = sorted(markets, key=lambda m: m.get('endDate', ''), reverse=False)
            
            for market in markets:
                market_id = market.get("id")
                title = market.get("question", market.get("title", ""))[:45]
                
                # Get probability and volume from market data
                # outcomePrices can be at top level or nested in markets[0]
                outcome_prices = market.get('outcomePrices')
                if not outcome_prices and market.get('markets') and len(market.get('markets', [])) > 0:
                    outcome_prices = market['markets'][0].get('outcomePrices')
                
                # Parse outcome prices (can be string "[\"0.5\", \"0.5\"]" or list)
                if isinstance(outcome_prices, str):
                    import json
                    try:
                        outcome_prices = json.loads(outcome_prices)
                    except Exception:
                        outcome_prices = None
                
                if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                    price = float(outcome_prices[0])
                else:
                    price = 0
                
                probability = price * 100 if price else 0
                volume_24hr = float(market.get('volume24hr', 0) or 0)
                
                # Calculate data age
                end_date_str = market.get('endDate', '')
                data_age = "Live"
                if end_date_str:
                    try:
                        if HAS_DATEUTIL:
                            end_date = date_parser.parse(end_date_str)
                        else:
                            end_date = datetime.fromisoformat(end_date_str.replace('Z', '+00:00'))
                        
                        # Make now timezone-aware to match end_date
                        from datetime import timezone
                        now_utc = datetime.now(timezone.utc)
                        
                        hours_until = (end_date - now_utc).total_seconds() / 3600
                        if hours_until > 24:
                            days_until = int(hours_until / 24)
                            data_age = f"{days_until}d"
                        elif hours_until > 0:
                            data_age = f"{int(hours_until)}h"
                        else:
                            data_age = "[red]Ended[/red]"
                    except Exception as e:
                        data_age = "?"
                
                # Format probability with color
                prob_style = "green" if probability > 50 else "yellow" if probability > 30 else "white"
                prob_text = f"[{prob_style}]{probability:.1f}%[/{prob_style}]"

                # Format volume
                volume_text = f"${volume_24hr:,.0f}" if volume_24hr > 0 else "[dim]$0[/dim]"

                # Volume quality indicator
                quality_text = ""
                if show_quality:
                    liquidity = float(market.get('liquidity', 0) or 0)
                    wash_score, _ = quick_wash_trade_score(volume_24hr, liquidity)
                    if wash_score >= 75:
                        quality_text = "[red]![/red]"  # Warning
                    elif wash_score >= 55:
                        quality_text = "[yellow]?[/yellow]"  # Caution
                    else:
                        quality_text = "[green]OK[/green]"  # Good

                if show_quality:
                    table.add_row(
                        title,
                        prob_text,
                        volume_text,
                        quality_text,
                        data_age,
                    )
                else:
                    table.add_row(
                        title,
                        prob_text,
                        volume_text,
                        data_age,
                    )
        
        except Exception as e:
            handle_api_error(console, e, "fetching markets")

        return table
    
    def get_markets_data():
        """Get filtered and sorted markets data"""
        try:
            # When filtering by category, fetch many more markets since we filter after
            fetch_limit = max(100, limit * 10) if category else limit

            if sort == 'volume':
                markets = aggregator.get_top_markets_by_volume(limit=fetch_limit, min_volume=0.01)
            else:
                markets = aggregator.get_live_markets(
                    limit=fetch_limit,
                    require_volume=True,
                    min_volume=0.01
                )

            if category:
                markets = [m for m in markets if matches_category(m, category)]
                markets = markets[:limit]  # Apply limit after filtering

            if active_only:
                markets = [m for m in markets if m.get('active', False) and not m.get('closed', True)]

            if sort == 'probability':
                def get_probability(m):
                    outcome_prices = m.get('outcomePrices')
                    if not outcome_prices and m.get('markets') and len(m.get('markets', [])) > 0:
                        outcome_prices = m['markets'][0].get('outcomePrices')
                    if isinstance(outcome_prices, str):
                        try:
                            outcome_prices = json.loads(outcome_prices)
                        except Exception:
                            return 0
                    if outcome_prices and isinstance(outcome_prices, list) and len(outcome_prices) > 0:
                        return float(outcome_prices[0])
                    return 0
                markets = sorted(markets, key=get_probability, reverse=True)
            elif sort == 'recent':
                markets = sorted(markets, key=lambda m: m.get('endDate', ''), reverse=False)

            return markets
        except Exception as e:
            return []

    # JSON output mode
    if output_format == 'json':
        try:
            markets = get_markets_data()
            output = {
                'success': True,
                'timestamp': datetime.now().isoformat(),
                'count': len(markets),
                'markets': format_markets_json(markets),
            }
            print_json(output)
        except Exception as e:
            print_json({'success': False, 'error': str(e)})
        finally:
            gamma_client.close()
            clob_client.close()
        return

    # Run once mode (for scripting)
    if once:
        table = generate_table()
        console.print(table)
        if table.row_count == 0:
            show_error(console, 'no_markets_found')
        gamma_client.close()
        clob_client.close()
        return

    # Live display
    try:
        with Live(generate_table(), refresh_per_second=1/refresh, console=console) as live:
            while True:
                time.sleep(refresh)
                live.update(generate_table())

    except KeyboardInterrupt:
        console.print("\n[yellow]Monitoring stopped[/yellow]")
    finally:
        gamma_client.close()
        clob_client.close()

