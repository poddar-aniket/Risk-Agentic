"""
Loads config/config.yaml and injects secrets from .env (never hardcode API
keys in config.yaml itself — see .env.example).
"""
import os

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_config(path: str = "config/config.yaml") -> dict:
    with open(path, "r") as f:
        config = yaml.safe_load(f)

    config.setdefault("llm", {})["api_key"] = os.getenv("GEMINI_API_KEY")
    config.setdefault("data_sources", {})
    config["data_sources"]["newsdata_api_key"] = os.getenv("NEWSDATA_API_KEY")
    config["data_sources"]["openweather_api_key"] = os.getenv("OPENWEATHER_API_KEY")
    return config
