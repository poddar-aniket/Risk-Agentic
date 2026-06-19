"""
TODO (Day 3/4 — owner: ash119821 / poddar-aniket): add decision-specific
queries as needed (e.g. pending_approvals()).
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.decision import Decision


class DecisionRepository(BaseRepository[Decision]):
    def __init__(self, db: Session):
        super().__init__(db, Decision)
