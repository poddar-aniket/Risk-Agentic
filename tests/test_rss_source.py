"""
tests/test_rss_source.py

Coverage for app/ingestion/rss.py's RSSDataSource.

MOCKING APPROACH, WORTH READING BEFORE TRUSTING THIS FILE:
feedparser.parse() normally returns a FeedParserDict -- a dict subclass
that ALSO supports attribute access (feed.feed.title works the same as
feed.feed.get("title")). rss.py's actual code only ever calls .get() on
feed.feed and on each entry (never attribute access) -- confirmed by
reading the real file, not assumed. Because of that, the fakes below use
plain dicts for feed.feed and for entries, NOT a real FeedParserDict and
NOT a MagicMock. This is deliberately the simplest fake that satisfies
exactly what rss.py's code path actually calls (.get() with various
default values), and no more. If a future edit to rss.py ever switches
from .get()-style access to attribute access anywhere, these fakes would
need to change too -- they are not a general-purpose feedparser stand-in,
they model this file's specific usage of it.

feedparser.parse is patched at the module level inside app.ingestion.rss,
not by hitting a real URL or a real feedparser fixture file.
"""
import pytest
from unittest.mock import MagicMock, patch

from app.ingestion import rss as rss_module
from app.ingestion.rss import RSSDataSource
from app.ingestion.base import RawArticle


def _fake_feed(feed_title=None, entries=None):
    """
    feed.feed is a dict-like with a "title" key (rss.py does
    feed.feed.get("title", url)). feed.entries is a list of dict-like
    entries (rss.py does entry.get(...) for summary/description/content/
    title/link/published).
    """
    fake = MagicMock()
    fake.feed = {"title": feed_title} if feed_title is not None else {}
    fake.entries = entries or []
    return fake


class TestRSSDataSource:
    def test_empty_feed_urls_returns_empty_list(self):
        source = RSSDataSource(feed_urls=[])
        with patch.object(rss_module.feedparser, "parse") as mock_parse:
            articles = source.fetch_events()
        assert articles == []
        mock_parse.assert_not_called()

    def test_none_feed_urls_defaults_to_empty_list(self):
        source = RSSDataSource(feed_urls=None)
        assert source.feed_urls == []

    def test_happy_path_maps_entry_to_raw_article(self):
        source = RSSDataSource(feed_urls=["https://example.com/feed.xml"])
        entry = {
            "title": "Port delays continue",
            "summary": "Summary text content.",
            "link": "https://example.com/article1",
            "published": "Sat, 20 Jun 2026 10:00:00 GMT",
        }
        fake_feed = _fake_feed(feed_title="Example News Feed", entries=[entry])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed):
            articles = source.fetch_events()

        assert len(articles) == 1
        article = articles[0]
        assert isinstance(article, RawArticle)
        assert article.source == "Example News Feed"
        assert article.title == "Port delays continue"
        assert article.content == "Summary text content."
        assert article.url == "https://example.com/article1"
        assert article.published_at == "Sat, 20 Jun 2026 10:00:00 GMT"

    def test_source_falls_back_to_url_when_feed_has_no_title(self):
        source = RSSDataSource(feed_urls=["https://example.com/feed.xml"])
        entry = {"title": "t", "summary": "s", "link": "l"}
        fake_feed = _fake_feed(feed_title=None, entries=[entry])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed):
            articles = source.fetch_events()

        assert articles[0].source == "https://example.com/feed.xml"

    def test_content_falls_back_to_description_when_summary_missing(self):
        source = RSSDataSource(feed_urls=["https://example.com/feed.xml"])
        entry = {"title": "t", "description": "Description fallback text.", "link": "l"}
        fake_feed = _fake_feed(feed_title="Feed", entries=[entry])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed):
            articles = source.fetch_events()

        assert articles[0].content == "Description fallback text."

    def test_content_falls_back_to_content_list_value_when_summary_and_description_missing(self):
        source = RSSDataSource(feed_urls=["https://example.com/feed.xml"])
        entry = {"title": "t", "content": [{"value": "Content list fallback text."}], "link": "l"}
        fake_feed = _fake_feed(feed_title="Feed", entries=[entry])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed):
            articles = source.fetch_events()

        assert articles[0].content == "Content list fallback text."

    def test_entry_with_no_usable_content_anywhere_is_skipped(self):
        source = RSSDataSource(feed_urls=["https://example.com/feed.xml"])
        no_content_entry = {"title": "Nothing usable", "link": "l"}
        has_content_entry = {"title": "Has content", "summary": "Real content", "link": "l2"}
        fake_feed = _fake_feed(feed_title="Feed", entries=[no_content_entry, has_content_entry])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed):
            articles = source.fetch_events()

        assert len(articles) == 1
        assert articles[0].title == "Has content"

    def test_multiple_feed_urls_aggregate_entries_from_all(self):
        source = RSSDataSource(feed_urls=["https://a.com/feed.xml", "https://b.com/feed.xml"])
        feed_a = _fake_feed(feed_title="Feed A", entries=[{"title": "A1", "summary": "sA", "link": "lA"}])
        feed_b = _fake_feed(feed_title="Feed B", entries=[{"title": "B1", "summary": "sB", "link": "lB"}])

        with patch.object(rss_module.feedparser, "parse", side_effect=[feed_a, feed_b]):
            articles = source.fetch_events()

        assert len(articles) == 2
        assert articles[0].source == "Feed A"
        assert articles[1].source == "Feed B"

    def test_feed_with_no_entries_produces_no_articles(self):
        source = RSSDataSource(feed_urls=["https://example.com/feed.xml"])
        fake_feed = _fake_feed(feed_title="Empty Feed", entries=[])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed):
            articles = source.fetch_events()

        assert articles == []

    def test_each_url_is_parsed_individually(self):
        source = RSSDataSource(feed_urls=["https://a.com/feed.xml", "https://b.com/feed.xml"])
        fake_feed = _fake_feed(feed_title="Feed", entries=[])

        with patch.object(rss_module.feedparser, "parse", return_value=fake_feed) as mock_parse:
            source.fetch_events()

        assert mock_parse.call_count == 2
        called_urls = [c.args[0] for c in mock_parse.call_args_list]
        assert called_urls == ["https://a.com/feed.xml", "https://b.com/feed.xml"]