"""
NewsData.io adapter (free tier).

TODO (Day 1 — owner: poddar-aniket):
- Use httpx to call the NewsData.io API with the configured query/params.
- Map the JSON response into a list[RawArticle].
"""
from app.ingestion.base import BaseDataSource, RawArticle


class NewsDataSource(BaseDataSource):
    def __init__(self, api_key: str = "", query: str = "", **kwargs):
        self.api_key = api_key
        self.query = query

    def fetch_events(self) -> list[RawArticle]:
        raise NotImplementedError("NewsData.io adapter — build on Day 1")
