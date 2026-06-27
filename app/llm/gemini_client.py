"""
GeminiClient — concrete LLMClient implementation using Gemini 2.5 Flash-Lite
via langchain-google-genai's structured-output binding.

The structured-output binding (.with_structured_output(schema)) is what lets
us hand it a Pydantic class and get back a validated instance of that class
directly, instead of parsing JSON out of free text ourselves.
"""
import logging
import time
from typing import Type, TypeVar

from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel

from app.llm.base import LLMClient

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class GeminiClient(LLMClient):
    def __init__(
        self,
        api_key: str,
        model_name: str = "gemini-3.1-flash-lite",
        max_retries: int = 3,
        temperature: float = 0.0,
    ):
        self.api_key = api_key
        self.model_name = model_name
        self.max_retries = max_retries
        self._model = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature,
        )

    def generate(self, prompt: str, output_schema: Type[T]) -> T:
        structured_model = self._model.with_structured_output(output_schema)

        last_exc: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            try:
                return structured_model.invoke(prompt)
            except Exception as exc:  # Gemini free-tier rate limits, transient API errors
                last_exc = exc
                wait_seconds = 2 ** attempt
                logger.warning(
                    "Gemini call failed (attempt %d/%d): %s — retrying in %ds",
                    attempt,
                    self.max_retries,
                    exc,
                    wait_seconds,
                )
                if attempt < self.max_retries:
                    time.sleep(wait_seconds)

        raise RuntimeError(f"Gemini generate() failed after {self.max_retries} attempts") from last_exc
