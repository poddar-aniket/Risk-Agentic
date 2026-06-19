"""
DecisionRepository — stores Decision Agent proposals and their approval status.
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.decision import Decision


class DecisionRepository(BaseRepository[Decision]):
    def __init__(self, db: Session):
        super().__init__(db, Decision)

    def get_pending(self) -> list[Decision]:
        """All decisions waiting for human approval — the approval queue."""
        return self.db.query(Decision).filter(Decision.status == "pending").all()

    def approve(self, decision_id: int) -> Decision | None:
        decision = self.get(decision_id)
        if decision is None:
            return None
        decision.status = "approved"
        self.db.commit()
        self.db.refresh(decision)
        return decision

    def reject(self, decision_id: int, reason: str) -> Decision | None:
        decision = self.get(decision_id)
        if decision is None:
            return None
        decision.status = "rejected"
        decision.rejection_reason = reason
        self.db.commit()
        self.db.refresh(decision)
        return decision
