"""
OpenWeatherMap adapter (free tier).

TODO (Day 1 — owner: poddar-aniket):
- httpx call per configured location.
- Map weather alerts/conditions into a list[RawArticle] (or a separate
  weather-specific shape if RawArticle doesn't fit cleanly — decide and
  document the choice here once you get to it).
"""
from app.ingestion.base import BaseDataSource, RawArticle


class OpenWeatherDataSource(BaseDataSource):
    def __init__(self, api_key: str = "", locations: list[str] | None = None, **kwargs):
        self.api_key = api_key
        self.locations = locations or []

    def fetch_events(self) -> list[RawArticle]:
        raise NotImplementedError("OpenWeatherMap adapter — build on Day 1")
