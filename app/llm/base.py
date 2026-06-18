"""
LLMClient — Strategy interface for LLM providers. GeminiClient is the only
current implementation; OpenAIClient can be added later as a second
implementation + a config change, with no agent code changes required.
"""
from abc import ABC, abstractmethod
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMClient(ABC):
    @abstractmethod
    def generate(self, prompt: str, output_schema: Type[T]) -> T:
        """Send `prompt` to the LLM and return a validated `output_schema` instance."""
        raise NotImplementedError
