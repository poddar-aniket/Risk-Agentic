from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class Event(Base):
    """TODO (Day 2 — owner: ash119821): finalize columns to mirror the
    Event Extraction Agent's Pydantic schema (type, location, severity, timeframe)."""

    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String)
    location = Column(String)
    severity = Column(Integer)
    raw_content = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
