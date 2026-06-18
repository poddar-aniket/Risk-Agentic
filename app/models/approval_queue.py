from sqlalchemy import Column, ForeignKey, Integer, String

from app.db.session import Base


class ApprovalQueue(Base):
    """TODO (Day 4 — owner: poddar-aniket): finalize columns; this likely
    just tracks decision_id + hitl_framing + queue status, since the full
    reasoning trail is reconstructed by joining back to Event/Decision."""

    __tablename__ = "approval_queue"

    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"))
    hitl_framing = Column(String)  # "high_confidence" | "low_confidence"
