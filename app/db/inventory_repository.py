"""
InventoryRepository — queries inventory state, used by Risk Analysis Agent
to judge supply buffer (days_of_stock_remaining) and by the Decision Agent
to size mitigation actions.
"""
from sqlalchemy.orm import Session

from app.db.base_repository import BaseRepository
from app.models.inventory import Inventory


class InventoryRepository(BaseRepository[Inventory]):
    def __init__(self, db: Session):
        super().__init__(db, Inventory)

    def get_by_supplier(self, supplier_id: int) -> list[Inventory]:
        return (
            self.db.query(Inventory)
            .filter(Inventory.supplier_id == supplier_id)
            .all()
        )

    def get_low_stock(self, threshold_days: float = 7.0) -> list[Inventory]:
        """Return inventory rows where days of stock remaining is below threshold.
        Used by Risk Analysis Agent to flag high-urgency situations."""
        rows = self.db.query(Inventory).all()
        return [r for r in rows if r.days_of_stock_remaining <= threshold_days]

    def update_stock(self, inventory_id: int, new_stock_level: float) -> Inventory | None:
        """Day 5 simulated execution: update stock level on approval."""
        row = self.get(inventory_id)
        if row is None:
            return None
        row.stock_level = new_stock_level
        self.db.commit()
        self.db.refresh(row)
        return row

    def mark_reorder_placed(self, inventory_id: int) -> Inventory | None:
        """Day 5 simulated execution: flag reorder as placed on approval."""
        row = self.get(inventory_id)
        if row is None:
            return None
        row.reorder_placed = True
        self.db.commit()
        self.db.refresh(row)
        return row
