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

# Maps each source type to the config["data_sources"] key its API key was
# injected under by load_config() (see app/utils/config.py). RSS has no
# entry here -- it needs no API key, feed URLs are public.
_API_KEY_CONFIG_KEYS = {
    "newsdata": "newsdata_api_key",
    "openweather": "openweather_api_key",
}


class SourceFactory:
    @staticmethod
    def create_all(config: dict) -> list[BaseDataSource]:
        sources = []
        data_sources_config = config.get("data_sources", {})

        for entry in data_sources_config.get("active", []):
            source_type = entry["type"]
            source_cls = _REGISTRY.get(source_type)
            if source_cls is None:
                raise ValueError(f"Unknown data source type: {source_type}")

            params = dict(entry.get("params", {}))

            # Inject the API key from its real config location (set by
            # load_config() from .env), not from config.yaml's params
            # block -- params never contains secrets.
            api_key_config_key = _API_KEY_CONFIG_KEYS.get(source_type)
            if api_key_config_key is not None:
                params["api_key"] = data_sources_config.get(api_key_config_key)

            sources.append(source_cls(**params))

        return sources