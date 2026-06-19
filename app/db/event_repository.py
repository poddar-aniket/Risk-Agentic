"""
TODO (Day 2 — owner: ash119821): add event-specific queries as needed
(e.g. by_date_range()).
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.event import Event


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: Session):
        super().__init__(db, Event)
