"""
GeminiClient — concrete LLMClient implementation using Gemini 2.5 Flash-Lite
via langchain-google-genai's structured-output binding.

TODO (Day 1 — owner: ash119821):
- from langchain_google_genai import ChatGoogleGenerativeAI
- self._model = ChatGoogleGenerativeAI(model=model_name, google_api_key=api_key)
- In generate(): return self._model.with_structured_output(output_schema).invoke(prompt)
- Add retry-with-backoff around the call (Gemini free tier rate limits).
"""
from typing import Type, TypeVar

from pydantic import BaseModel

from app.llm.base import LLMClient

T = TypeVar("T", bound=BaseModel)


class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model_name: str = "gemini-2.5-flash-lite"):
        self.api_key = api_key
        self.model_name = model_name

    def generate(self, prompt: str, output_schema: Type[T]) -> T:
        raise NotImplementedError("Wire up ChatGoogleGenerativeAI structured output — Day 1")
