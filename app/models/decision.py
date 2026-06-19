from sqlalchemy import Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from app.db.session import Base


class Decision(Base):
    """TODO (Day 3/4 — owner: ash119821): finalize columns to mirror the
    Decision Agent's structured output (action type, target supplier/product,
    justification, magnitude) plus supervisor confidence + status."""

    __tablename__ = "decisions"

    id = Column(Integer, primary_key=True)
    action_type = Column(String)
    target = Column(String)
    justification = Column(Text)
    confidence_score = Column(Float)
    status = Column(String, default="pending")  # "pending" | "approved" | "rejected"
    rejection_reason = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
