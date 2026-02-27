"""News Aggregation Engine

Aggregates market-relevant news from RSS feeds and matches
articles to prediction markets by keyword overlap.
"""

import time
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, timezone

import requests


class NewsAggregator:
    """Aggregate market-relevant news from multiple RSS sources"""

    DEFAULT_FEEDS = [
        ("The Block", "https://www.theblock.co/rss.xml"),
        ("CoinDesk", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
        ("Decrypt", "https://decrypt.co/feed"),
    ]

    def __init__(self, feeds=None, cache_ttl=300):
        """Initialize news aggregator

        Args:
            feeds: List of (name, url) tuples for RSS feeds
            cache_ttl: Cache time-to-live in seconds (default 5 min)
        """
        self.feeds = feeds or self.DEFAULT_FEEDS
        self.cache = {}
        self.cache_ttl = cache_ttl
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'PolyTerm/0.9.0 News Reader',
        })

    def fetch_feed(self, name, url):
        """Fetch and parse a single RSS feed

        Args:
            name: Feed name for display
            url: RSS feed URL

        Returns:
            List of article dicts with title, link, published, summary, source
        """
        # Check cache
        cache_key = url
        cache_entry = self.cache.get(cache_key)
        if cache_entry:
            cached_time, cached_data = cache_entry
            if time.time() - cached_time < self.cache_ttl:
                return cached_data

        try:
            articles = []
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)

            # Handle both RSS 2.0 and Atom feeds
            # RSS 2.0: channel/item
            items = root.findall('.//item')
            if not items:
                # Atom: entry
                ns = {'atom': 'http://www.w3.org/2005/Atom'}
                items = root.findall('.//atom:entry', ns)

            for item in items:
                article = self._parse_item(item, name)
                if article:
                    articles.append(article)

        except Exception:
            # Preserve stale data on transient errors, but keep retries enabled.
            if cache_entry:
                _, cached_data = cache_entry
                return cached_data
            return []

        # Cache successful parses (including legitimately empty feeds).
        self.cache[cache_key] = (time.time(), articles)
        return articles

    def _parse_item(self, item, source_name):
        """Parse a single RSS item/entry into an article dict"""
        # Try RSS 2.0 format first
        title = self._get_text(item, 'title')
        link = self._get_text(item, 'link')
        pub_date = self._get_text(item, 'pubDate') or self._get_text(item, 'published')
        summary = self._get_text(item, 'description') or self._get_text(item, 'summary')

        # Try Atom format
        if not title:
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            title_el = item.find('atom:title', ns)
            if title_el is not None:
                title = title_el.text
            link_el = item.find('atom:link', ns)
            if link_el is not None:
                link = link_el.get('href', '')
            pub_el = item.find('atom:published', ns)
            if pub_el is None:
                pub_el = item.find('atom:updated', ns)
            if pub_el is not None:
                pub_date = pub_el.text
            summary_el = item.find('atom:summary', ns)
            if summary_el is None:
                summary_el = item.find('atom:content', ns)
            if summary_el is not None:
                summary = self._extract_all_text(summary_el)

        if not title:
            return None

        published_dt = self._parse_published_datetime(pub_date)

        # Clean summary (strip HTML tags)
        clean_summary = ''
        if summary:
            import re
            clean_summary = re.sub(r'<[^>]+>', '', summary)
            clean_summary = clean_summary.strip()
            clean_summary = clean_summary[:200]

        return {
            'title': title.strip(),
            'link': link.strip() if link else '',
            'published': published_dt.isoformat() if published_dt else '',
            'published_dt': published_dt,
            'summary': clean_summary,
            'source': source_name,
        }

    def _normalize_datetime(self, dt):
        """Normalize datetimes to UTC and make them timezone-aware."""
        if dt is None:
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def _parse_published_datetime(self, pub_date):
        """Parse published date strings across RSS/Atom formats."""
        if not pub_date:
            return None

        text = str(pub_date).strip()

        for fmt in [
            "%a, %d %b %Y %H:%M:%S %z",
            "%a, %d %b %Y %H:%M:%S GMT",
            "%Y-%m-%dT%H:%M:%S.%f%z",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
        ]:
            try:
                return self._normalize_datetime(datetime.strptime(text, fmt))
            except ValueError:
                continue

        try:
            normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
            return self._normalize_datetime(datetime.fromisoformat(normalized))
        except ValueError:
            return None

    def _get_text(self, element, tag):
        """Safely get text from an XML element, including nested tags"""
        child = element.find(tag)
        if child is not None:
            # Get all text content recursively (handles nested HTML tags)
            return self._extract_all_text(child)
        return None

    def _extract_all_text(self, element):
        """Recursively extract all text from an element and its children"""
        text_parts = []
        if element.text:
            text_parts.append(element.text)
        for child in element:
            # Recurse into children
            text_parts.append(self._extract_all_text(child))
            if child.tail:
                text_parts.append(child.tail)
        return ''.join(text_parts)

    def fetch_all(self):
        """Fetch all configured news feeds

        Returns:
            List of all articles from all feeds, sorted by recency
        """
        all_articles = []
        for name, url in self.feeds:
            articles = self.fetch_feed(name, url)
            all_articles.extend(articles)

        # Sort by published date (newest first)
        min_dt = datetime.min.replace(tzinfo=timezone.utc)
        all_articles.sort(
            key=lambda a: a.get('published_dt') or min_dt,
            reverse=True,
        )
        return all_articles

    def match_to_markets(self, articles, markets):
        """Match news articles to relevant markets by keyword overlap

        Args:
            articles: List of article dicts
            markets: List of market dicts with 'title' or 'question' key

        Returns:
            Dict mapping market titles to lists of matching articles
        """
        matches = {}

        for market in markets:
            market_title = market.get('title', market.get('question', ''))
            if not market_title:
                continue

            market_words = set(market_title.lower().split())
            # Remove common words
            stop_words = {'the', 'a', 'an', 'will', 'be', 'by', 'in', 'on', 'to', 'of', '?', 'is', 'it', 'and', 'or'}
            market_words -= stop_words

            if len(market_words) < 1:
                continue

            market_matches = []
            for article in articles:
                article_title = article.get('title', '').lower()
                article_words = set(article_title.split()) - stop_words

                # Check keyword overlap - require at least 1 significant word
                overlap = market_words & article_words
                if len(overlap) >= 1:
                    market_matches.append(article)

            if market_matches:
                matches[market_title] = market_matches

        return matches

    def get_market_news(self, market_title, limit=5, hours=None):
        """Get news relevant to a specific market

        Args:
            market_title: Market question/title to match against
            limit: Max articles to return
            hours: Optional recency filter window

        Returns:
            List of matching article dicts
        """
        all_articles = self.fetch_all()
        cutoff = None
        if hours is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        market_words = set(market_title.lower().split())
        stop_words = {'the', 'a', 'an', 'will', 'be', 'by', 'in', 'on', 'to', 'of', '?', 'is', 'it', 'and', 'or'}
        market_words -= stop_words

        if len(market_words) < 1:
            return []

        matches = []
        for article in all_articles:
            if cutoff is not None:
                pub_dt = self._normalize_datetime(article.get('published_dt'))
                # Apply a strict recency filter when requested.
                if pub_dt is None or pub_dt < cutoff:
                    continue

            text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
            text_words = set(text.split()) - stop_words

            overlap = market_words & text_words
            # Match if we have at least 1 significant word overlap
            if len(overlap) >= 1:
                matches.append(article)

        return matches[:limit]

    def get_breaking_news(self, hours=6, limit=20):
        """Get recent breaking news across all feeds

        Args:
            hours: How far back to look
            limit: Max articles to return

        Returns:
            List of recent article dicts
        """
        all_articles = self.fetch_all()
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)

        recent = []
        for article in all_articles:
            pub_dt = self._normalize_datetime(article.get('published_dt'))
            if pub_dt:
                if pub_dt >= cutoff:
                    recent.append(article)
            else:
                # No date, include it (might be recent)
                recent.append(article)

        return recent[:limit]

    def close(self):
        """Close the session"""
        self.session.close()
