"""
NewsData.io adapter (free tier).
Fetches latest news articles matching the configured query and maps them
into RawArticle instances for the pipeline.
"""
import httpx
from app.ingestion.base import BaseDataSource, RawArticle


class NewsDataSource(BaseDataSource):
    BASE_URL = "https://newsdata.io/api/1/news"

    def __init__(self, api_key: str = "", query: str = "", **kwargs):
        self.api_key = api_key
        self.query = query

    def fetch_events(self) -> list[RawArticle]:
        if not self.api_key:
            raise ValueError("NEWSDATA_API_KEY is not set")

        params = {
            "apikey": self.api_key,
            "q": self.query,
            "language": "en",
            "category": "business,science,technology",
        }

        response = httpx.get(self.BASE_URL, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        articles = []
        for item in data.get("results", []):
            content = item.get("content") or item.get("description") or ""
            if "ONLY AVAILABLE IN PAID PLANS" in content:
                content = item.get("description") or ""
            if not content:
                continue
            articles.append(RawArticle(
                source="newsdata.io",
                title=item.get("title", ""),
                content=content,
                url=item.get("link"),
                published_at=item.get("pubDate"),
            ))

        return articles