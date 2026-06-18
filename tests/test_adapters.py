import os
from dotenv import load_dotenv
from app.ingestion.newsdata import NewsDataSource
from app.ingestion.rss import RSSDataSource
from app.ingestion.openweather import OpenWeatherDataSource

load_dotenv()

# Test NewsData.io
print("--- NewsData.io ---")
news = NewsDataSource(
    api_key=os.getenv("NEWSDATA_API_KEY", ""),
    query="supply chain disruption India"
)
articles = news.fetch_events()
print(f"Fetched {len(articles)} articles")
for a in articles[:2]:
    print(f"  [{a.source}] {a.title[:60]}")
    print(f"  {a.content[:100]}...")

# Test RSS (using a real public feed)
print("\n--- RSS ---")
rss = RSSDataSource(feed_urls=["https://feeds.feedburner.com/ndtvnews-top-stories"])
rss_articles = rss.fetch_events()
print(f"Fetched {len(rss_articles)} articles")
for a in rss_articles[:2]:
    print(f"  [{a.source}] {a.title[:60]}")
# Test OpenWeatherMap
print("\n--- OpenWeatherMap ---")
weather = OpenWeatherDataSource(
    api_key=os.getenv("OPENWEATHER_API_KEY", ""),
    locations=["Mumbai", "Delhi", "Chennai"]
)

from app.ingestion.openweather import OpenWeatherDataSource
weather_articles = weather.fetch_events()
print(f"Fetched {len(weather_articles)} articles")
for a in weather_articles:
    print(f"  [{a.source}] {a.title}")
    print(f"  {a.content}")