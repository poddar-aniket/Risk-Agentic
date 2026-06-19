"""
LLMClient factory — instantiates the configured provider. Adding OpenAIClient
later means a new class + one new branch here, no agent code changes.
"""
from app.llm.base import LLMClient
from app.llm.gemini_client import GeminiClient


def create_llm_client(config: dict) -> LLMClient:
    provider = config.get("llm", {}).get("provider", "gemini")
    if provider == "gemini":
        return GeminiClient(
            api_key=config["llm"]["api_key"],
            model_name=config["llm"].get("model_name", "gemini-2.5-flash-lite"),
        )
    raise ValueError(f"Unknown LLM provider: {provider}")
