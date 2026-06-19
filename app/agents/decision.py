"""
Decision Agent — proposes a concrete mitigation action grounded in:
  - risk_assessment  (Risk Analysis Agent)
  - supplier_impact  (Supplier Agent)
  - RAG: similar past cases + previously rejected options

The key behaviour: before proposing anything, it queries RAG for previously
rejected options so the same bad idea isn't proposed twice for similar situations.
The rejection reason (stored by the FastAPI reject endpoint on Day 4) is what
makes this useful — it's the human's domain knowledge fed back into the loop.

Reads from state:  risk_assessment, supplier_impact
Writes to state:   decision_proposal (DecisionProposal)
"""
import logging

from sqlalchemy.orm import Session

from app.agents.base import BaseAgent
from app.agents.schemas import DecisionProposal
from app.db.inventory_repository import InventoryRepository
from app.llm.base import LLMClient
from app.rag.client import RAGClient
from app.state import PipelineState

logger = logging.getLogger(__name__)

DECISION_PROMPT_TEMPLATE = """You are a supply-chain risk mitigation specialist. Your job is to propose ONE concrete mitigation action for a supply-chain disruption.

You will be given:
1. The risk assessment (score, rationale, urgency)
2. The affected suppliers and their current inventory levels
3. Similar past cases and their outcomes from our historical database
4. Previously rejected mitigation options — you MUST NOT propose any of these again

AVAILABLE ACTION TYPES:
- place_reorder: Place an urgent reorder for a specific product from a supplier
- find_alternate_supplier: Identify and engage an alternate supplier in a different region
- increase_safety_stock: Increase safety stock buffer for a high-risk product
- hold_supplier: Flag a supplier as on-hold and pause new orders
- expedite_shipment: Expedite an existing order via faster transport
- monitor_only: No action needed yet — continue monitoring

DECISION RULES:
- If days_of_stock_remaining < reorder_lead_time: place_reorder is likely needed
- If risk_score >= 8 and no alternate suppliers exist: find_alternate_supplier
- If risk_score <= 3: monitor_only is appropriate
- NEVER propose an action that appears in the previously rejected options list
- Propose the SINGLE most impactful action — not a list

RISK ASSESSMENT:
Score: {risk_score}/10
Urgency: {urgency}
Rationale: {rationale}
Affected products: {affected_products}

SUPPLIER AND INVENTORY DATA:
{inventory_context}

SIMILAR PAST CASES FROM HISTORICAL DATABASE:
{rag_context}

PREVIOUSLY REJECTED OPTIONS (DO NOT PROPOSE THESE):
{rejected_options}

Based on all of the above, propose ONE concrete mitigation action. Be specific about magnitude (exact units, timeframes, quantities). Justify your choice by referencing the actual numbers above."""


def _format_inventory_context(supplier_impact: dict) -> str:
    rows = supplier_impact.get("inventory_summary", [])
    if not rows:
        return "No inventory data available."
    lines = []
    for row in rows:
        days = row.get("days_of_stock_remaining")
        days_str = f"{days}" if days is not None else "∞"
        reorder_status = "YES" if row.get("reorder_placed") else "no"
        lines.append(
            f"- {row['product']} | Supplier: {row['supplier_name']} | "
            f"Stock: {row['stock_level']} units | Days remaining: {days_str} | "
            f"Lead time: {row['reorder_lead_time']}d | Reorder placed: {reorder_status}"
        )
    return "\n".join(lines)


def _format_rag_context(results: list[dict]) -> str:
    if not results:
        return "No similar historical cases found."
    lines = []
    for i, r in enumerate(results, 1):
        doc = r.get("document", "")
        meta = r.get("metadata", {})
        lines.append(f"Case {i}: {doc} | Outcome: {meta.get('outcome', '?')} | Duration: {meta.get('duration_days', '?')}d")
    return "\n".join(lines)


def _format_rejected_options(results: list[dict]) -> str:
    if not results:
        return "None — no previously rejected options on record for similar situations."
    lines = []
    for i, r in enumerate(results, 1):
        doc = r.get("document", "")
        meta = r.get("metadata", {})
        reason = meta.get("rejection_reason", "no reason recorded")
        lines.append(f"{i}. {doc} — Rejected because: {reason}")
    return "\n".join(lines)


class DecisionAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, db: Session, rag_client: RAGClient):
        super().__init__(llm_client)
        self.inventory_repo = InventoryRepository(db)
        self.rag_client = rag_client

    def run(self, state: PipelineState) -> PipelineState:
        if state.risk_assessment is None:
            raise ValueError("DecisionAgent requires state.risk_assessment")
        if state.supplier_impact is None:
            raise ValueError("DecisionAgent requires state.supplier_impact")

        risk = state.risk_assessment
        impact = state.supplier_impact

        # build a query string for RAG lookups
        products_str = ", ".join(impact.get("affected_products", []))
        rag_query = f"mitigation for {risk.get('urgency', '')} risk disruption affecting {products_str}"

        # fetch similar past cases
        past_cases = self.rag_client.query(rag_query, top_k=5)

        # fetch previously rejected options — stored with metadata type="rejection"
        rejected_query = f"rejected mitigation {products_str}"
        rejected_results = self.rag_client.query(rejected_query, top_k=5)
        # filter to only rejection records (Aniket's RAG seed will tag these)
        rejected_options = [
            r for r in rejected_results
            if r.get("metadata", {}).get("record_type") == "rejection"
        ]

        prompt = DECISION_PROMPT_TEMPLATE.format(
            risk_score=risk.get("risk_score", "?"),
            urgency=risk.get("urgency", "?"),
            rationale=risk.get("rationale", ""),
            affected_products=products_str,
            inventory_context=_format_inventory_context(impact),
            rag_context=_format_rag_context(past_cases),
            rejected_options=_format_rejected_options(rejected_options),
        )

        proposal: DecisionProposal = self.llm_client.generate(prompt, DecisionProposal)

        # mark that we did check for rejected options
        proposal_dict = proposal.model_dump(mode="json")
        proposal_dict["previously_rejected_options_checked"] = True

        state.decision_proposal = proposal_dict
        logger.info(
            "DecisionAgent: proposed action=%s for product=%s supplier=%s",
            proposal.action_type,
            proposal.target_product,
            proposal.target_supplier_name,
        )
        return state
