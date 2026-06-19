"""
Risk Analysis Agent — the heart of the pipeline.

Reads from PipelineState:
  - structured_event  (Event Extraction Agent, Day 1)
  - affected_regions  (Geo Agent, Day 2 Aniket)

Fetches from DB:
  - Suppliers in affected regions (SupplierRepository)
  - Inventory levels for those suppliers (InventoryRepository)

Fetches from RAG:
  - Top-k similar past disruption cases + their outcomes

Produces:
  - risk_assessment (RiskAssessment) written to state

The score is the LLM's rubric-based judgment grounded in real numeric
context — not a formula in code. The prompt supplies the actual numbers
(days of stock, % of supply at risk, historical durations from RAG) and
a rubric; the LLM reasons over them.
"""
import logging

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.schemas import RiskAssessment
from app.db.inventory_repository import InventoryRepository
from app.db.supplier_repository import SupplierRepository
from app.llm.base import LLMClient
from app.rag.client import RAGClient
from app.state import PipelineState

logger = logging.getLogger(__name__)

RISK_ANALYSIS_PROMPT_TEMPLATE = """You are a supply-chain risk analyst. Your job is to produce a structured risk assessment for a real-world disruption event.

You will be given:
1. The structured event details
2. The regions and transport routes affected (from the Geo Agent)
3. Real supplier and inventory data for the affected region
4. Similar past disruption cases retrieved from our historical database

Your risk score must be grounded in the rubric below and the actual numbers provided — do not guess or use generic assumptions:

SCORING RUBRIC:
1-3: Minor/localized disruption. Affected suppliers cover < 10% of supply. Buffer > 30 days. Historical cases resolved quickly.
4-6: Moderate disruption. Some key suppliers or routes affected. Buffer 15-30 days. Some historical cases caused delays.
7-8: Serious disruption. Multiple suppliers/products at risk. Buffer < 14 days. Historical cases caused significant stockouts.
9-10: Critical. Imminent stockout risk (< 7 days buffer) OR major multi-region collapse OR no alternative suppliers available.

EVENT DETAILS:
Type: {event_type}
Locations: {locations}
Severity (as reported): {event_severity}/10
Status: {timeframe_status}
Estimated duration: {duration} days
Summary: {event_summary}

AFFECTED REGIONS AND ROUTES (from Geo Agent):
{affected_regions}

SUPPLIER AND INVENTORY DATA FOR AFFECTED REGIONS:
{supplier_inventory_context}

SIMILAR PAST CASES FROM HISTORICAL DATABASE:
{rag_context}

Based on all of the above, produce a structured risk assessment. Be specific in your rationale — reference the actual days of stock remaining, supplier names, and historical precedent."""


def _format_supplier_inventory(suppliers, inventory_repo: InventoryRepository) -> str:
    if not suppliers:
        return "No suppliers found in the directly affected regions."

    lines = []
    for supplier in suppliers:
        inventory_rows = inventory_repo.get_by_supplier(supplier.id)
        lines.append(f"Supplier: {supplier.name} (Region: {supplier.region}, Status: {supplier.status})")
        if not inventory_rows:
            lines.append("  No inventory data found.")
        for row in inventory_rows:
            days_left = row.days_of_stock_remaining
            days_str = f"{days_left:.1f}" if days_left != float("inf") else "∞"
            lines.append(
                f"  Product: {row.product} | Stock: {row.stock_level} units | "
                f"Daily use: {row.avg_daily_consumption} | Days remaining: {days_str} | "
                f"Lead time: {row.reorder_lead_time}d | Reorder placed: {row.reorder_placed}"
            )
    return "\n".join(lines)


def _format_rag_context(rag_results: list[dict]) -> str:
    if not rag_results:
        return "No similar historical cases found in the database."
    lines = []
    for i, result in enumerate(rag_results, 1):
        doc = result.get("document", "")
        metadata = result.get("metadata", {})
        lines.append(f"Case {i}: {doc}")
        if metadata:
            lines.append(
    f"  Days to resolve: {metadata.get('days_to_resolve', '?')}, "
    f"Historical delay: {metadata.get('historical_delay_days', '?')} days"
)
    return "\n".join(lines)


class RiskAnalysisAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, db: Session, rag_client: RAGClient):
        super().__init__(llm_client)
        self.supplier_repo = SupplierRepository(db)
        self.inventory_repo = InventoryRepository(db)
        self.rag_client = rag_client

    def run(self, state: PipelineState) -> PipelineState:
        if state.structured_event is None:
            raise ValueError("RiskAnalysisAgent requires state.structured_event")
        if state.affected_regions is None:
            raise ValueError("RiskAnalysisAgent requires state.affected_regions (from Geo Agent)")

        event = state.structured_event
        affected_regions = state.affected_regions

        # fetch suppliers in affected regions
        region_names: list[str] = affected_regions.get("primary_regions", [])
        suppliers = []
        for region in region_names:
            suppliers.extend(self.supplier_repo.get_by_region(region))
        # deduplicate by id
        seen_ids = set()
        unique_suppliers = []
        for s in suppliers:
            if s.id not in seen_ids:
                unique_suppliers.append(s)
                seen_ids.add(s.id)

        supplier_inventory_context = _format_supplier_inventory(unique_suppliers, self.inventory_repo)

        # build a RAG query from the event summary + locations
        rag_query = f"{event.get('event_type', '')} disruption in {', '.join(event.get('locations', []))}"
        rag_results = self.rag_client.query(
    collection_name="past_events",
    query_text=rag_query,
    top_k=5,
)
        rag_context = _format_rag_context(rag_results)

        prompt = RISK_ANALYSIS_PROMPT_TEMPLATE.format(
            event_type=event.get("event_type", ""),
            locations=", ".join(event.get("locations", [])),
            event_severity=event.get("severity", "unknown"),
            timeframe_status=event.get("timeframe_status", ""),
            duration=event.get("estimated_duration_days", "unknown"),
            event_summary=event.get("summary", ""),
            affected_regions=affected_regions.get("description", str(affected_regions)),
            supplier_inventory_context=supplier_inventory_context,
            rag_context=rag_context,
        )

        assessment: RiskAssessment = self.llm_client.generate(prompt, RiskAssessment)

        state.risk_assessment = assessment.model_dump(mode="json")
        logger.info(
            "Risk assessment complete: score=%d, urgency=%s",
            assessment.risk_score,
            assessment.urgency,
        )
        return state
