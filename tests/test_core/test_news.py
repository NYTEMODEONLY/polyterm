"""Tests for NewsAggregator"""

import pytest
import responses
from datetime import datetime, timedelta, timezone
from unittest.mock import patch, MagicMock

from polyterm.core.news import NewsAggregator


# Sample RSS 2.0 XML responses
RSS_FEED_VALID = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Bitcoin Surges Past $100K</title>
      <link>https://example.com/1</link>
      <pubDate>Mon, 03 Feb 2026 12:00:00 +0000</pubDate>
      <description>Bitcoin has surged past the $100,000 mark</description>
    </item>
    <item>
      <title>Ethereum Updates Coming Soon</title>
      <link>https://example.com/2</link>
      <pubDate>Mon, 03 Feb 2026 10:00:00 +0000</pubDate>
      <description><p>Ethereum network <strong>upgrade</strong> scheduled</p></description>
    </item>
  </channel>
</rss>"""

RSS_FEED_EMPTY = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Empty Feed</title>
  </channel>
</rss>"""

RSS_FEED_NO_DATES = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Article Without Date</title>
      <link>https://example.com/3</link>
      <description>No date here</description>
    </item>
  </channel>
</rss>"""

RSS_FEED_MALFORMED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Missing closing tag
    </item>
"""

RSS_FEED_MIXED_DATES = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>GMT Format Article</title>
      <link>https://example.com/4</link>
      <pubDate>Mon, 03 Feb 2026 12:00:00 GMT</pubDate>
      <description>GMT date format</description>
    </item>
    <item>
      <title>Offset Format Article</title>
      <link>https://example.com/5</link>
      <pubDate>Mon, 03 Feb 2026 10:00:00 +0000</pubDate>
      <description>Offset date format</description>
    </item>
  </channel>
</rss>"""

ATOM_FEED_LEAF_FIELDS = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test Feed</title>
  <entry>
    <title>Atom BTC Headline</title>
    <link href="https://example.com/atom-1" />
    <published>2026-02-03T12:00:00Z</published>
    <summary>Atom summary without child nodes</summary>
  </entry>
</feed>"""

ATOM_FEED_NESTED_SUMMARY = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Nested Feed</title>
  <entry>
    <title>Atom Nested Summary Headline</title>
    <link href="https://example.com/atom-2" />
    <published>2026-02-03T12:00:00Z</published>
    <summary><p>Will Bitcoin <em>rally</em> today</p></summary>
  </entry>
</feed>"""


class TestFetchFeed:
    """Tests for fetch_feed method"""

    @responses.activate
    def test_successful_rss_parsing(self):
        """Should parse valid RSS feed successfully"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert len(articles) == 2
        assert articles[0]['title'] == "Bitcoin Surges Past $100K"
        assert articles[0]['link'] == "https://example.com/1"
        assert articles[0]['source'] == "Test"
        assert "Bitcoin has surged" in articles[0]['summary']

    @responses.activate
    def test_empty_feed(self):
        """Should handle empty RSS feed gracefully"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_EMPTY,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert articles == []

    @responses.activate
    def test_network_error(self):
        """Should handle network errors gracefully"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body="Network error",
            status=500,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        # Should return empty list on error
        assert articles == []

    @responses.activate
    def test_transient_failure_does_not_cache_empty_results(self):
        """Should retry immediately after a transient fetch failure."""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body="Network error",
            status=500,
        )
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")], cache_ttl=300)

        first = aggregator.fetch_feed("Test", "https://test.com/feed.xml")
        second = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert first == []
        assert len(second) == 2
        assert len(responses.calls) == 2

    @responses.activate
    def test_cache_behavior(self):
        """Should use cache on second call"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")], cache_ttl=300)

        # First call - should hit network
        articles1 = aggregator.fetch_feed("Test", "https://test.com/feed.xml")
        assert len(articles1) == 2
        assert len(responses.calls) == 1

        # Second call - should use cache
        articles2 = aggregator.fetch_feed("Test", "https://test.com/feed.xml")
        assert len(articles2) == 2
        assert len(responses.calls) == 1  # No additional network call

    @responses.activate
    def test_cache_expiry(self):
        """Should fetch new data after cache expires"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")], cache_ttl=1)

        # First call
        articles1 = aggregator.fetch_feed("Test", "https://test.com/feed.xml")
        assert len(articles1) == 2
        assert len(responses.calls) == 1

        # Mock time passing
        with patch('time.time') as mock_time:
            mock_time.return_value = aggregator.cache["https://test.com/feed.xml"][0] + 2

            # Should fetch again
            articles2 = aggregator.fetch_feed("Test", "https://test.com/feed.xml")
            assert len(articles2) == 2
            assert len(responses.calls) == 2

    @responses.activate
    def test_malformed_xml(self):
        """Should handle malformed XML gracefully"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_MALFORMED,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        # Should return empty list on parse error
        assert articles == []

    @responses.activate
    def test_keeps_stale_cache_on_transient_failure(self):
        """Should return stale cached data if refresh attempt fails."""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body="Network error",
            status=500,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")], cache_ttl=1)
        first = aggregator.fetch_feed("Test", "https://test.com/feed.xml")
        cached_time, _ = aggregator.cache["https://test.com/feed.xml"]

        with patch('time.time') as mock_time:
            mock_time.return_value = cached_time + 2
            second = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert len(first) == 2
        assert len(second) == 2
        assert len(responses.calls) == 2
        assert aggregator.cache["https://test.com/feed.xml"][0] == cached_time


class TestParsing:
    """Tests for RSS parsing logic"""

    @responses.activate
    def test_rss_20_item_parsing(self):
        """Should parse RSS 2.0 items correctly"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        article = articles[0]
        assert article['title'] == "Bitcoin Surges Past $100K"
        assert article['link'] == "https://example.com/1"
        assert article['source'] == "Test"
        assert article['published'] != ''
        assert article['published_dt'] is not None
        assert "Bitcoin has surged" in article['summary']

    @responses.activate
    def test_atom_leaf_nodes_parse_published_and_summary(self):
        """Should parse Atom fields even when elements have no child nodes."""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=ATOM_FEED_LEAF_FIELDS,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert len(articles) == 1
        article = articles[0]
        assert article['title'] == "Atom BTC Headline"
        assert article['link'] == "https://example.com/atom-1"
        assert article['published_dt'] is not None
        assert article['published'] != ''
        assert article['summary'] == "Atom summary without child nodes"

    @responses.activate
    def test_atom_nested_summary_text_is_preserved(self):
        """Should extract text from nested Atom summary markup."""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=ATOM_FEED_NESTED_SUMMARY,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert len(articles) == 1
        assert "Will Bitcoin rally today" in articles[0]['summary']

    @responses.activate
    def test_various_date_formats(self):
        """Should parse various date formats"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_MIXED_DATES,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert len(articles) == 2
        # Both should have parsed dates
        assert articles[0]['published_dt'] is not None
        assert articles[1]['published_dt'] is not None
        assert articles[0]['published_dt'].tzinfo is not None
        assert articles[1]['published_dt'].tzinfo is not None

    @responses.activate
    def test_html_stripping_from_summary(self):
        """Should strip HTML tags from summary"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        # Second article has HTML in description
        article = articles[1]
        assert '<p>' not in article['summary']
        assert '<strong>' not in article['summary']
        assert 'Ethereum network upgrade scheduled' in article['summary']

    @responses.activate
    def test_missing_fields_handled(self):
        """Should handle articles with missing fields"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_NO_DATES,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_feed("Test", "https://test.com/feed.xml")

        assert len(articles) == 1
        article = articles[0]
        assert article['title'] == "Article Without Date"
        assert article['published'] == ''
        assert article['published_dt'] is None


class TestFetchAll:
    """Tests for fetch_all method"""

    @responses.activate
    def test_fetches_all_feeds(self):
        """Should fetch articles from all configured feeds"""
        responses.add(
            responses.GET,
            "https://feed1.com/rss",
            body=RSS_FEED_VALID,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://feed2.com/rss",
            body=RSS_FEED_NO_DATES,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[
            ("Feed1", "https://feed1.com/rss"),
            ("Feed2", "https://feed2.com/rss"),
        ])
        articles = aggregator.fetch_all()

        # Should have articles from both feeds
        assert len(articles) >= 2
        sources = {a['source'] for a in articles}
        assert 'Feed1' in sources
        assert 'Feed2' in sources

    @responses.activate
    def test_sorts_by_date(self):
        """Should sort articles by date (newest first)"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_all()

        # Articles should be sorted newest first
        for i in range(len(articles) - 1):
            if articles[i]['published_dt'] and articles[i+1]['published_dt']:
                assert articles[i]['published_dt'] >= articles[i+1]['published_dt']

    @responses.activate
    def test_sorts_mixed_naive_and_aware_dates(self):
        """Should normalize mixed date formats before sorting."""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_MIXED_DATES,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.fetch_all()

        assert len(articles) == 2
        assert all(a['published_dt'].tzinfo is not None for a in articles if a['published_dt'])
        assert articles[0]['published_dt'] >= articles[1]['published_dt']

    @responses.activate
    def test_handles_partial_feed_failures(self):
        """Should continue if some feeds fail"""
        responses.add(
            responses.GET,
            "https://feed1.com/rss",
            body=RSS_FEED_VALID,
            status=200,
        )
        responses.add(
            responses.GET,
            "https://feed2.com/rss",
            body="Error",
            status=500,
        )

        aggregator = NewsAggregator(feeds=[
            ("Feed1", "https://feed1.com/rss"),
            ("Feed2", "https://feed2.com/rss"),
        ])
        articles = aggregator.fetch_all()

        # Should still have articles from successful feed
        assert len(articles) > 0
        assert all(a['source'] == 'Feed1' for a in articles)


class TestMatchToMarkets:
    """Tests for match_to_markets method"""

    def test_keyword_matching_works(self):
        """Should match articles to markets by keyword overlap"""
        articles = [
            {
                'title': 'Bitcoin Surges Past $100K',
                'link': 'https://example.com/1',
                'published': '',
                'published_dt': None,
                'summary': '',
                'source': 'Test',
            },
            {
                'title': 'Ethereum Updates Coming Soon',
                'link': 'https://example.com/2',
                'published': '',
                'published_dt': None,
                'summary': '',
                'source': 'Test',
            },
        ]

        markets = [
            {'title': 'Will Bitcoin reach $100K by 2026?'},
            {'title': 'Will Ethereum merge succeed?'},
        ]

        aggregator = NewsAggregator()
        matches = aggregator.match_to_markets(articles, markets)

        assert 'Will Bitcoin reach $100K by 2026?' in matches
        assert len(matches['Will Bitcoin reach $100K by 2026?']) == 1
        assert matches['Will Bitcoin reach $100K by 2026?'][0]['title'] == 'Bitcoin Surges Past $100K'

    def test_stop_words_ignored(self):
        """Should ignore common stop words in matching"""
        articles = [
            {
                'title': 'Major Bitcoin News',
                'link': 'https://example.com/1',
                'published': '',
                'published_dt': None,
                'summary': '',
                'source': 'Test',
            },
        ]

        markets = [
            {'title': 'Will the Bitcoin price be high?'},
        ]

        aggregator = NewsAggregator()
        matches = aggregator.match_to_markets(articles, markets)

        # Should match on 'Bitcoin' despite different stop words
        assert 'Will the Bitcoin price be high?' in matches

    def test_no_overlap_returns_empty(self):
        """Should return empty dict when no matches"""
        articles = [
            {
                'title': 'Bitcoin News',
                'link': 'https://example.com/1',
                'published': '',
                'published_dt': None,
                'summary': '',
                'source': 'Test',
            },
        ]

        markets = [
            {'title': 'Will Ethereum merge succeed?'},
        ]

        aggregator = NewsAggregator()
        matches = aggregator.match_to_markets(articles, markets)

        assert matches == {}

    def test_multiple_market_matches(self):
        """Should match article to multiple markets if relevant"""
        articles = [
            {
                'title': 'Bitcoin and Ethereum Rally Together',
                'link': 'https://example.com/1',
                'published': '',
                'published_dt': None,
                'summary': '',
                'source': 'Test',
            },
        ]

        markets = [
            {'title': 'Will Bitcoin reach $100K?'},
            {'title': 'Will Ethereum reach $10K?'},
        ]

        aggregator = NewsAggregator()
        matches = aggregator.match_to_markets(articles, markets)

        # Both markets should match
        assert len(matches) == 2


class TestGetMarketNews:
    """Tests for get_market_news method"""

    @responses.activate
    def test_finds_relevant_articles(self):
        """Should find articles relevant to market"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_market_news("Bitcoin price prediction", limit=5)

        assert len(articles) > 0
        # Should match Bitcoin article
        assert any('Bitcoin' in a['title'] for a in articles)

    @responses.activate
    def test_no_matches_returns_empty(self):
        """Should return empty list when no matches"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_VALID,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_market_news("Solana ecosystem growth", limit=5)

        # No Solana articles in feed
        assert articles == []

    @responses.activate
    def test_respects_limit(self):
        """Should respect limit parameter"""
        # Create feed with many matching articles
        many_articles_feed = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item><title>Bitcoin Article 1</title><link>https://example.com/1</link></item>
    <item><title>Bitcoin Article 2</title><link>https://example.com/2</link></item>
    <item><title>Bitcoin Article 3</title><link>https://example.com/3</link></item>
    <item><title>Bitcoin Article 4</title><link>https://example.com/4</link></item>
    <item><title>Bitcoin Article 5</title><link>https://example.com/5</link></item>
    <item><title>Bitcoin Article 6</title><link>https://example.com/6</link></item>
  </channel>
</rss>"""

        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=many_articles_feed,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_market_news("Bitcoin", limit=3)

        assert len(articles) <= 3

    @responses.activate
    def test_respects_hours_filter(self):
        """Should apply hours filter for market-specific queries."""
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(hours=30)).strftime("%a, %d %b %Y %H:%M:%S %z")
        recent_date = (now - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S %z")

        mixed_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Old Bitcoin Article</title>
      <link>https://example.com/old</link>
      <pubDate>{old_date}</pubDate>
      <description>Old bitcoin story</description>
    </item>
    <item>
      <title>Recent Bitcoin Article</title>
      <link>https://example.com/recent</link>
      <pubDate>{recent_date}</pubDate>
      <description>Recent bitcoin story</description>
    </item>
  </channel>
</rss>"""

        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=mixed_feed,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_market_news("Bitcoin", limit=10, hours=6)

        assert len(articles) == 1
        assert articles[0]["title"] == "Recent Bitcoin Article"


class TestGetBreakingNews:
    """Tests for get_breaking_news method"""

    @responses.activate
    def test_filters_by_hours(self):
        """Should filter articles by time window"""
        # Create feed with old and new articles
        now = datetime.now(timezone.utc)
        old_date = (now - timedelta(hours=25)).strftime("%a, %d %b %Y %H:%M:%S %z")
        recent_date = (now - timedelta(hours=2)).strftime("%a, %d %b %Y %H:%M:%S %z")

        mixed_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item>
      <title>Recent Article</title>
      <link>https://example.com/1</link>
      <pubDate>{recent_date}</pubDate>
    </item>
    <item>
      <title>Old Article</title>
      <link>https://example.com/2</link>
      <pubDate>{old_date}</pubDate>
    </item>
  </channel>
</rss>"""

        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=mixed_feed,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_breaking_news(hours=6, limit=20)

        # Should only include recent article
        assert len(articles) == 1
        assert articles[0]['title'] == "Recent Article"

    @responses.activate
    def test_no_date_articles_included(self):
        """Should include articles without dates"""
        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=RSS_FEED_NO_DATES,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_breaking_news(hours=6, limit=20)

        # Should include article without date
        assert len(articles) == 1
        assert articles[0]['title'] == "Article Without Date"

    @responses.activate
    def test_respects_limit(self):
        """Should respect limit parameter"""
        # Create many recent articles
        now = datetime.now(timezone.utc)
        recent_date = (now - timedelta(hours=1)).strftime("%a, %d %b %Y %H:%M:%S %z")

        many_articles = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test Feed</title>
    <item><title>Article 1</title><link>https://example.com/1</link><pubDate>{recent_date}</pubDate></item>
    <item><title>Article 2</title><link>https://example.com/2</link><pubDate>{recent_date}</pubDate></item>
    <item><title>Article 3</title><link>https://example.com/3</link><pubDate>{recent_date}</pubDate></item>
    <item><title>Article 4</title><link>https://example.com/4</link><pubDate>{recent_date}</pubDate></item>
    <item><title>Article 5</title><link>https://example.com/5</link><pubDate>{recent_date}</pubDate></item>
  </channel>
</rss>"""

        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=many_articles,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_breaking_news(hours=6, limit=3)

        assert len(articles) <= 3

    @responses.activate
    def test_fractional_second_atom_dates_respect_hours_filter(self):
        """Should parse fractional-second Atom timestamps for recency filtering."""
        old_iso = (datetime.now(timezone.utc) - timedelta(hours=25)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        atom_feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Test Feed</title>
  <entry>
    <title>Old Atom Article</title>
    <link href="https://example.com/atom-old" />
    <published>{old_iso}</published>
    <summary>Old summary</summary>
  </entry>
</feed>"""

        responses.add(
            responses.GET,
            "https://test.com/feed.xml",
            body=atom_feed,
            status=200,
        )

        aggregator = NewsAggregator(feeds=[("Test", "https://test.com/feed.xml")])
        articles = aggregator.get_breaking_news(hours=6, limit=20)

        assert articles == []
