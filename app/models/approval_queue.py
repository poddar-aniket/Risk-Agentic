from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, func

from app.db.session import Base


class ApprovalQueue(Base):
    """Tracks how a finalized decision is surfaced to a human reviewer on
    the dashboard, separate from the decision's own approved/rejected/
    pending lifecycle (see Decision.status).

    Written once per decision when the micro-loop exits (see graph.py's
    hitl_framing_node) -- owned by app/orchestration/scheduler.py, not yet
    built. The full reasoning trail is reconstructed by joining back to
    Decision (and Event, once event persistence is wired up), not
    duplicated here as JSON blobs.
    """

    __tablename__ = "approval_queue"

    id = Column(Integer, primary_key=True)
    decision_id = Column(Integer, ForeignKey("decisions.id"), nullable=False)
    hitl_framing = Column(String, nullable=False)  # "high_confidence" | "low_confidence"
    status = Column(String, default="unread")  # "unread" | "viewed"
    created_at = Column(DateTime, server_default=func.now())