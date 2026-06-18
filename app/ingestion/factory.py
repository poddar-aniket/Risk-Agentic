"""
SourceFactory — instantiates the active data sources listed in config.yaml.
Adding a source = new adapter class + a registry entry + a config.yaml block;
no changes anywhere else in the pipeline (Open/Closed Principle).
"""
from app.ingestion.base import BaseDataSource
from app.ingestion.newsdata import NewsDataSource
from app.ingestion.openweather import OpenWeatherDataSource
from app.ingestion.rss import RSSDataSource

_REGISTRY = {
    "newsdata": NewsDataSource,
    "rss": RSSDataSource,
    "openweather": OpenWeatherDataSource,
}


class SourceFactory:
    @staticmethod
    def create_all(config: dict) -> list[BaseDataSource]:
        sources = []
        for entry in config.get("data_sources", {}).get("active", []):
            source_cls = _REGISTRY.get(entry["type"])
            if source_cls is None:
                raise ValueError(f"Unknown data source type: {entry['type']}")
            sources.append(source_cls(**entry.get("params", {})))
        return sources
