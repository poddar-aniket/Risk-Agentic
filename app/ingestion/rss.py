"""
RSS adapter via feedparser.
Parses one or more RSS feed URLs and maps entries into RawArticle instances.
"""
import feedparser
from app.ingestion.base import BaseDataSource, RawArticle


class RSSDataSource(BaseDataSource):
    def __init__(self, feed_urls: list[str] | None = None, **kwargs):
        self.feed_urls = feed_urls or []

    def fetch_events(self) -> list[RawArticle]:
        articles = []

        for url in self.feed_urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                content = (
                    entry.get("summary")
                    or entry.get("description")
                    or entry.get("content", [{}])[0].get("value", "")
                )
                if not content:
                    continue
                articles.append(RawArticle(
                    source=feed.feed.get("title", url),
                    title=entry.get("title", ""),
                    content=content,
                    url=entry.get("link"),
                    published_at=entry.get("published"),
                ))

        return articles