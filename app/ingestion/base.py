"""
BaseDataSource — pluggable data source interface. Adding a new source means
a new subclass + a config.yaml entry; SourceFactory and the rest of the
pipeline don't change.
"""
from abc import ABC, abstractmethod
from typing import Optional

from pydantic import BaseModel


class RawArticle(BaseModel):
    """Raw, unstructured article/event data as fetched from any source."""

    source: str
    title: str
    content: str
    url: Optional[str] = None
    published_at: Optional[str] = None


class BaseDataSource(ABC):
    @abstractmethod
    def fetch_events(self) -> list[RawArticle]:
        raise NotImplementedError
