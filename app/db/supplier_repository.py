"""
TODO (Day 2 — owner: ash119821): add supplier-specific queries beyond the
generic CRUD (e.g. by_region(), by_status()) as the agents need them.
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.supplier import Supplier


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, db: Session):
        super().__init__(db, Supplier)
