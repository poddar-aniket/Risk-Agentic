"""
SupplierRepository — domain-specific queries on top of generic CRUD.
Agents call these rather than writing raw SQLAlchemy, keeping agent code
decoupled from the DB layer.
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.supplier import Supplier


class SupplierRepository(BaseRepository[Supplier]):
    def __init__(self, db: Session):
        super().__init__(db, Supplier)

    def get_by_region(self, region: str) -> list[Supplier]:
        """Return all active suppliers whose region matches (case-insensitive partial match).
        Used by the Supplier Agent to map affected_regions -> specific suppliers."""
        return (
            self.db.query(Supplier)
            .filter(
                Supplier.region.ilike(f"%{region}%"),
                Supplier.status == "active",
            )
            .all()
        )

    def get_by_status(self, status: str) -> list[Supplier]:
        """Return all suppliers with a given status — e.g. all on_hold suppliers."""
        return self.db.query(Supplier).filter(Supplier.status == status).all()

    def set_status(self, supplier_id: int, status: str) -> Supplier | None:
        """Update a supplier's status (e.g. active -> on_hold on Day 5 approval).
        Returns the updated supplier, or None if not found."""
        supplier = self.get(supplier_id)
        if supplier is None:
            return None
        supplier.status = status
        self.db.commit()
        self.db.refresh(supplier)
        return supplier

    def get_by_product(self, product: str) -> list[Supplier]:
        """Return all active suppliers whose products_supplied CSV contains the product."""
        return (
            self.db.query(Supplier)
            .filter(
                Supplier.products_supplied.ilike(f"%{product}%"),
                Supplier.status == "active",
            )
            .all()
        )
