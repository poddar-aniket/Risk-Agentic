"""
OpenWeatherMap adapter (free tier).
Fetches current weather conditions for configured locations and maps
significant weather into RawArticle instances for the pipeline.
We use RawArticle here — weather alerts are treated as events just like
news articles; the Event Extraction Agent will interpret them accordingly.
"""
import httpx
from app.ingestion.base import BaseDataSource, RawArticle


class OpenWeatherDataSource(BaseDataSource):
    BASE_URL = "https://api.openweathermap.org/data/2.5/weather"

    def __init__(self, api_key: str = "", locations: list[str] | None = None, **kwargs):
        self.api_key = api_key
        self.locations = locations or []

    def fetch_events(self) -> list[RawArticle]:
        if not self.api_key:
            raise ValueError("OPENWEATHER_API_KEY is not set")

        articles = []

        for location in self.locations:
            params = {
                "q": location,
                "appid": self.api_key,
                "units": "metric",
            }

            response = httpx.get(self.BASE_URL, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()

            weather_desc = data.get("weather", [{}])[0].get("description", "")
            temp = data.get("main", {}).get("temp", "")
            wind_speed = data.get("wind", {}).get("speed", "")
            city = data.get("name", location)
            country = data.get("sys", {}).get("country", "")

            content = (
                f"Current weather in {city}, {country}: {weather_desc}. "
                f"Temperature: {temp}°C. Wind speed: {wind_speed} m/s."
            )

            articles.append(RawArticle(
                source="openweathermap",
                title=f"Weather update: {city}, {country}",
                content=content,
                url=None,
                published_at=None,
            ))

        return articles