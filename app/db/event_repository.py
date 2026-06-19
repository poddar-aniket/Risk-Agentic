"""
EventRepository — stores pipeline events and lets the system query recent ones.
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.event import Event


class EventRepository(BaseRepository[Event]):
    def __init__(self, db: Session):
        super().__init__(db, Event)

    def get_recent(self, limit: int = 20) -> list[Event]:
        """Most recent events first — used by the scheduler to avoid reprocessing."""
        return (
            self.db.query(Event)
            .order_by(Event.created_at.desc())
            .limit(limit)
            .all()
        )

    def get_by_type(self, event_type: str) -> list[Event]:
        return self.db.query(Event).filter(Event.event_type == event_type).all()

    def from_structured_event(self, structured_event: dict, raw_content: str = "") -> Event:
        """Convenience: build an Event model from a structured_event dict
        (the output of EventExtractionAgent) and persist it."""
        locations_csv = ",".join(structured_event.get("locations", []))
        event = Event(
            event_type=structured_event.get("event_type", ""),
            locations=locations_csv,
            severity=structured_event.get("severity", 1),
            timeframe_status=structured_event.get("timeframe_status", ""),
            estimated_duration_days=structured_event.get("estimated_duration_days"),
            summary=structured_event.get("summary", ""),
            raw_content=raw_content,
            is_relevant=1 if structured_event.get("is_relevant", True) else 0,
        )
        return self.add(event)
