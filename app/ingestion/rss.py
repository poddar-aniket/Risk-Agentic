"""
RSS adapter via feedparser.

TODO (Day 1 — owner: poddar-aniket):
- feedparser.parse(url) for each configured feed_url.
- Map entries into a list[RawArticle].
"""
from app.ingestion.base import BaseDataSource, RawArticle


class RSSDataSource(BaseDataSource):
    def __init__(self, feed_urls: list[str] | None = None, **kwargs):
        self.feed_urls = feed_urls or []

    def fetch_events(self) -> list[RawArticle]:
        raise NotImplementedError("RSS adapter — build on Day 1")
