"""
Event DB model — columns mirror the Event Extraction Agent's Pydantic schema
so a structured_event dict can be stored directly after each pipeline run.
locations is stored as a comma-separated string (simple, no join table needed
for a 4-5 day build; easy to split back into a list on read).
"""
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    event_type = Column(String, nullable=False)
    locations = Column(String)           # CSV: "Chennai,Tamil Nadu"
    severity = Column(Integer, nullable=False)
    timeframe_status = Column(String)    # "ongoing" | "resolved" | "expected"
    estimated_duration_days = Column(Integer, nullable=True)
    summary = Column(Text)
    raw_content = Column(Text)           # original article text, kept for audit
    is_relevant = Column(Integer, default=1)  # 1 = True, 0 = False (SQLite bool)
    created_at = Column(DateTime, server_default=func.now())
