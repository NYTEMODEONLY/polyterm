# News Aggregation Engine

> Aggregates market-relevant news from RSS feeds and matches articles to prediction markets by keyword overlap.

## Overview

The news module fetches articles from crypto/prediction-market RSS feeds (The Block, CoinDesk, Decrypt), parses both RSS 2.0 and Atom formats, and matches articles to Polymarket markets using keyword overlap. A time-based cache (default 5 minutes) reduces redundant network requests, and stale cache data is preserved on transient fetch errors.

## Key Classes and Functions

### `NewsAggregator`

Main class for fetching, parsing, caching, and matching news articles.

**Constructor**: `__init__(self, feeds=None, cache_ttl=300)`

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `feeds` | `List[Tuple[str, str]]` | `DEFAULT_FEEDS` | List of `(name, url)` tuples for RSS sources |
| `cache_ttl` | `int` | `300` | Cache time-to-live in seconds (5 minutes) |

#### Key Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `fetch_feed` | `(name: str, url: str) -> List[dict]` | Fetches and parses a single RSS feed. Returns cached data if within TTL. On error, returns stale cached data if available. |
| `fetch_all` | `() -> List[dict]` | Fetches all configured feeds and returns articles sorted by published date (newest first). |
| `match_to_markets` | `(articles: List[dict], markets: List[dict]) -> Dict[str, List[dict]]` | Matches articles to markets by keyword overlap. Returns a dict mapping market titles to lists of matching articles. |
| `get_market_news` | `(market_title: str, limit: int = 5, hours: Optional[int] = None) -> List[dict]` | Gets news relevant to a specific market. Matches against both title and summary text. Optional recency filter. |
| `get_breaking_news` | `(hours: int = 6, limit: int = 20) -> List[dict]` | Returns recent articles within the specified time window across all feeds. |
| `close` | `() -> None` | Closes the underlying HTTP session. |

#### Internal Methods

| Method | Signature | Description |
|--------|-----------|-------------|
| `_parse_item` | `(item: Element, source_name: str) -> Optional[dict]` | Parses a single RSS/Atom item into an article dict. Strips HTML from summaries (truncated to 200 chars). |
| `_parse_published_datetime` | `(pub_date: str) -> Optional[datetime]` | Parses date strings across 7+ format patterns (RFC 2822, ISO 8601, etc.). Normalizes all to UTC. |
| `_normalize_datetime` | `(dt: datetime) -> Optional[datetime]` | Converts naive datetimes to UTC-aware; converts aware datetimes to UTC. |
| `_get_text` | `(element: Element, tag: str) -> Optional[str]` | Safely extracts text from XML elements including nested tags. |
| `_extract_all_text` | `(element: Element) -> str` | Recursively extracts all text content from an XML element tree. |

## Scoring / Algorithms

### Keyword Matching

1. **Tokenize** market title and article title/summary into word sets (lowercased).
2. **Remove stop words**: `the`, `a`, `an`, `will`, `be`, `by`, `in`, `on`, `to`, `of`, `?`, `is`, `it`, `and`, `or`.
3. **Match threshold**: At least 1 significant word overlap required.
4. For `get_market_news()`, matching is performed against both article title and summary text combined.
5. For `match_to_markets()`, matching uses article titles only.

### Caching Strategy

- Each feed URL is cached independently with a `(timestamp, articles)` tuple.
- Cache hit: if `time.time() - cached_time < cache_ttl`, return cached data.
- On fetch error: return stale cached data if available; otherwise return empty list.
- Successful fetches (including empty feeds) always update the cache.

## Configuration

| Constant | Value | Description |
|----------|-------|-------------|
| Default cache TTL | `300` seconds (5 min) | Time before re-fetching a feed |
| HTTP timeout | `10` seconds | Per-feed request timeout |
| Summary truncation | `200` characters | Max length of cleaned article summaries |
| User-Agent | `PolyTerm/{polyterm.__version__} News Reader` | HTTP User-Agent header |

### Default RSS Feeds

| Source | URL |
|--------|-----|
| The Block | `https://www.theblock.co/rss.xml` |
| CoinDesk | `https://www.coindesk.com/arc/outboundfeeds/rss/` |
| Decrypt | `https://decrypt.co/feed` |

## Data Sources

- **RSS feeds**: The Block, CoinDesk, Decrypt (configurable)
- Supports both RSS 2.0 (`<item>`) and Atom (`<entry>`) feed formats

## Output Format

Article dict structure returned by all fetch methods:

```python
{
    'title': str,          # Article headline (stripped)
    'link': str,           # URL to full article
    'published': str,      # ISO format datetime string
    'published_dt': datetime,  # Parsed datetime object (UTC-aware) or None
    'summary': str,        # HTML-stripped summary (max 200 chars)
    'source': str,         # Feed name (e.g., "The Block")
}
```

`match_to_markets()` returns `Dict[str, List[dict]]` mapping market titles to article lists.

## External Dependencies

- `requests` -- HTTP client for fetching RSS feeds
- `xml.etree.ElementTree` -- RSS/Atom XML parsing (stdlib)

## Related

- CLI command: `polyterm news --hours 12 --limit 15`
- TUI screen: shortcut `nw`
- Used by prediction and analytics features for market context
