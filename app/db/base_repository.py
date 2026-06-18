"""
BaseRepository — generic Repository pattern. Decouples agents/API routes from
raw SQLAlchemy session calls, and is what makes a future SQLite -> Postgres
migration a one-line DATABASE_URL change instead of a rewrite.
"""
from abc import ABC
from typing import Generic, Optional, Type, TypeVar

from sqlalchemy.orm import Session

ModelT = TypeVar("ModelT")


class BaseRepository(ABC, Generic[ModelT]):
    def __init__(self, db: Session, model: Type[ModelT]):
        self.db = db
        self.model = model

    def get(self, id: int) -> Optional[ModelT]:
        return self.db.query(self.model).filter(self.model.id == id).first()

    def list(self) -> list[ModelT]:
        return self.db.query(self.model).all()

    def add(self, obj: ModelT) -> ModelT:
        self.db.add(obj)
        self.db.commit()
        self.db.refresh(obj)
        return obj

    def delete(self, obj: ModelT) -> None:
        self.db.delete(obj)
        self.db.commit()
