"""
Supplier Agent — maps affected_regions from the Geo Agent to specific
suppliers and products using the DB repositories.

This agent does NOT call the LLM — it's pure data retrieval and assembly.
The LLM reasoning about which regions are affected already happened in the
Geo Agent; this agent's job is to translate that into concrete supplier/
inventory records that the Decision Agent can act on.

Reads from state:  affected_regions (Geo Agent output)
Writes to state:   supplier_impact (SupplierImpact)
"""
import logging

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.schemas import SupplierImpact
from app.db.inventory_repository import InventoryRepository
from app.db.supplier_repository import SupplierRepository
from app.llm.base import LLMClient
from app.state import PipelineState

logger = logging.getLogger(__name__)


class SupplierAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, db: Session):
        super().__init__(llm_client)
        self.supplier_repo = SupplierRepository(db)
        self.inventory_repo = InventoryRepository(db)

    def run(self, state: PipelineState) -> PipelineState:
        if state.affected_regions is None:
            raise ValueError("SupplierAgent requires state.affected_regions (from Geo Agent)")

        region_names: list[str] = state.affected_regions.get("primary_regions", [])

        # fetch all active suppliers in affected regions, deduplicated by id
        suppliers = []
        seen_ids: set[int] = set()
        for region in region_names:
            for supplier in self.supplier_repo.get_by_region(region):
                if supplier.id not in seen_ids:
                    suppliers.append(supplier)
                    seen_ids.add(supplier.id)

        if not suppliers:
            logger.warning("SupplierAgent: no active suppliers found in regions %s", region_names)

        # build inventory summary across all affected suppliers
        affected_products: set[str] = set()
        inventory_summary: list[dict] = []

        for supplier in suppliers:
            inventory_rows = self.inventory_repo.get_by_supplier(supplier.id)
            for row in inventory_rows:
                affected_products.add(row.product)
                days_left = row.days_of_stock_remaining
                inventory_summary.append({
                    "product": row.product,
                    "supplier_name": supplier.name,
                    "supplier_id": supplier.id,
                    "stock_level": row.stock_level,
                    "avg_daily_consumption": row.avg_daily_consumption,
                    "days_of_stock_remaining": round(days_left, 1) if days_left != float("inf") else None,
                    "reorder_lead_time": row.reorder_lead_time,
                    "reorder_threshold": row.reorder_threshold,
                    "reorder_placed": row.reorder_placed,
                })

        impact = SupplierImpact(
            affected_suppliers=[
                {
                    "id": s.id,
                    "name": s.name,
                    "region": s.region,
                    "products_supplied": s.products_supplied,
                    "status": s.status,
                }
                for s in suppliers
            ],
            affected_products=sorted(affected_products),
            inventory_summary=inventory_summary,
            total_suppliers_affected=len(suppliers),
        )

        state.supplier_impact = impact.model_dump()
        logger.info(
            "SupplierAgent: found %d suppliers, %d products affected",
            len(suppliers),
            len(affected_products),
        )
        return state
