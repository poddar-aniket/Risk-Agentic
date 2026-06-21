"""
ApprovalQueueRepository — domain-specific queries on top of generic CRUD.

Written by scheduler.py once per decision, immediately after the micro
loop exits and hitl_framing is known (see app/orchestration/graph.py's
hitl_framing_node). One ApprovalQueue row corresponds to exactly one
Decision row (decision_id FK) -- this table tracks how that decision is
SURFACED to a human reviewer, not the decision itself.
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.approval_queue import ApprovalQueue


class ApprovalQueueRepository(BaseRepository[ApprovalQueue]):
    def __init__(self, db: Session):
        super().__init__(db, ApprovalQueue)

    def get_unread(self) -> list[ApprovalQueue]:
        """All queue items a human hasn't viewed yet — likely what the
        dashboard's default queue view will query against once the
        frontend exists."""
        return (
            self.db.query(ApprovalQueue)
            .filter(ApprovalQueue.status == "unread")
            .all()
        )

    def get_by_decision_id(self, decision_id: int) -> ApprovalQueue | None:
        """Look up the queue entry for a given decision -- useful for the
        approve/reject routes if they ever need to also mark the queue
        item as viewed, not just mutate the underlying Decision."""
        return (
            self.db.query(ApprovalQueue)
            .filter(ApprovalQueue.decision_id == decision_id)
            .first()
        )

    def mark_viewed(self, queue_id: int) -> ApprovalQueue | None:
        """Flip status from 'unread' to 'viewed'. Returns the updated row,
        or None if not found."""
        item = self.get(queue_id)
        if item is None:
            return None
        item.status = "viewed"
        self.db.commit()
        self.db.refresh(item)
        return item