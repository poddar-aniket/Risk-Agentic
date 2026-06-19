# app/agents/supplier.py

"""
Supplier Agent.

Maps the regions/suppliers already identified upstream (Geo Agent's
affected_regions, Risk Analysis Agent's affected_supplier_names) onto full
supplier and inventory records from the mock dataset, and structures them
into a clean SupplierImpact for the Decision Agent to size mitigations from.

Design note: unlike Geo / Risk Analysis / Decision / Supervisor, this agent
does NOT call the LLM. See chat discussion -- the judgment calls this agent
would otherwise make have already been made upstream; this agent's job is
deterministic structuring/lookup, not fresh reasoning.
"""
import logging

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.schemas import SupplierImpact
from app.db.inventory_repository import InventoryRepository
from app.db.supplier_repository import SupplierRepository
from app.llm.base import LLMClient
from app.models.supplier import Supplier
from app.state import PipelineState

logger = logging.getLogger(__name__)


class SupplierAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, db: Session):
        # llm_client is accepted to satisfy BaseAgent's constructor contract
        # and keep dependency injection consistent across all six agents,
        # but is intentionally unused -- see module docstring.
        super().__init__(llm_client)
        self.supplier_repo = SupplierRepository(db)
        self.inventory_repo = InventoryRepository(db)

    def run(self, state: PipelineState) -> PipelineState:
        if state.affected_regions is None:
            raise ValueError("SupplierAgent requires state.affected_regions (from Geo Agent)")
        if state.risk_assessment is None:
            raise ValueError("SupplierAgent requires state.risk_assessment (from Risk Analysis Agent)")

        affected_regions = state.affected_regions
        risk_assessment = state.risk_assessment

        candidates: dict[int, Supplier] = {}

        # Primary signal: suppliers the Risk Analysis Agent's LLM call
        # already named explicitly while scoring the risk.
        for name in risk_assessment.get("affected_supplier_names", []):
            for supplier in self.supplier_repo.get_by_name(name):
                candidates[supplier.id] = supplier

        # Supplementary signal: other active suppliers in the affected
        # regions the risk-scoring pass may not have explicitly named (it
        # was scoring risk, not enumerating every supplier in the area).
        for region in affected_regions.get("primary_regions", []):
            for supplier in self.supplier_repo.get_by_region(region):
                candidates[supplier.id] = supplier

        if not candidates:
            logger.warning(
                "SupplierAgent found no matching suppliers for regions=%s, named_suppliers=%s",
                affected_regions.get("primary_regions", []),
                risk_assessment.get("affected_supplier_names", []),
            )
            state.supplier_impact = SupplierImpact().model_dump(mode="json")
            return state

        affected_suppliers = []
        inventory_summary = []
        products_seen: set[str] = set()

        for supplier in candidates.values():
            affected_suppliers.append(
                {
                    "id": supplier.id,
                    "name": supplier.name,
                    "region": supplier.region,
                    "products_supplied": supplier.products_supplied,
                    "status": supplier.status,
                }
            )
            for row in self.inventory_repo.get_by_supplier(supplier.id):
                products_seen.add(row.product)
                days_remaining = row.days_of_stock_remaining
                inventory_summary.append(
                    {
                        "product": row.product,
                        "supplier_name": supplier.name,
                        "stock_level": row.stock_level,
                        "avg_daily_consumption": row.avg_daily_consumption,
                        # float("inf") isn't valid JSON -- normalize to None
                        # (= no tracked draw-down, effectively unlimited
                        # buffer) here rather than at every consumer.
                        "days_of_stock_remaining": (
                            None if days_remaining == float("inf") else round(days_remaining, 1)
                        ),
                        "reorder_lead_time": row.reorder_lead_time,
                        "reorder_placed": row.reorder_placed,
                    }
                )

        impact = SupplierImpact(
            affected_suppliers=affected_suppliers,
            affected_products=sorted(products_seen),
            inventory_summary=inventory_summary,
            total_suppliers_affected=len(candidates),
        )
        state.supplier_impact = impact.model_dump(mode="json")
        logger.info(
            "SupplierAgent identified %d suppliers, %d products at risk.",
            impact.total_suppliers_affected,
            len(impact.affected_products),
        )
        return state