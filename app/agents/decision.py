# app/agents/decision.py

"""
Decision Agent.

Proposes ONE concrete mitigation action, grounded in:
  - state.risk_assessment   (Risk Analysis Agent)
  - state.supplier_impact   (Supplier Agent, Day 3)
  - RAG "rejections" collection -- previously rejected proposals for similar
    situations, so the same option isn't proposed twice.

One half of the Decision <-> Supervisor micro loop. On the first pass
(state.supervisor_feedback is None) it builds a fresh proposal. On later
passes -- the LangGraph conditional edge has looped back from Supervisor --
it revises the previous proposal against the Supervisor's critique instead
of starting over.

Note: this agent does NOT increment state.iteration_count -- that's
Supervisor Agent / the conditional edge's responsibility, since Supervisor
is the one deciding whether the loop continues.
"""
import json
import logging

from app.agents.base import BaseAgent
from app.agents.schemas import DecisionProposal
from app.llm.base import LLMClient
from app.rag.client import RAGClient
from app.state import PipelineState

logger = logging.getLogger(__name__)

DECISION_PROMPT_TEMPLATE = """You are a supply-chain mitigation strategist for an India-focused retail company.

Your job is to propose ONE concrete, specific mitigation action in response to a supply-chain
disruption that has already been risk-scored and mapped to specific suppliers and inventory.
Ground every part of your proposal in the actual numbers provided below -- do not propose vague
or generic actions, and do not invent supplier or product names that aren't listed below.

RISK ASSESSMENT:
Risk score: {risk_score}/10 (urgency: {urgency})
Rationale: {risk_rationale}

AFFECTED SUPPLIERS AND INVENTORY:
{supplier_inventory_context}

PAST PROPOSALS REJECTED BY HUMANS FOR SIMILAR SITUATIONS -- DO NOT PROPOSE THESE AGAIN,
or if nothing else fits, explain in your justification why this case differs enough to proceed anyway:
{rejected_context}
{revision_context}
ACTION TYPES AVAILABLE: place_reorder, find_alternate_supplier, increase_safety_stock,
hold_supplier, expedite_shipment, monitor_only.

Choose the action type, target supplier, and target product that best matches the severity
and specifics of this situation. Size the action (magnitude) using the actual stock numbers
above -- e.g. if a product has 4 days of stock left and a 10-day lead time, a reorder sized to
cover the gap is appropriate; if a supplier has ample buffer, monitor_only may be the right call.

If no specific supplier or product was identified for this event, set action_type to
monitor_only, target_supplier_name and target_product to "none identified", and use the
justification to explain why no specific action is being taken yet.

Write a justification that explicitly references the risk score, the specific days-of-stock
number driving your decision, and any relevant historical precedent.
"""


def _format_supplier_inventory(supplier_impact: dict) -> str:
    inventory_summary = supplier_impact.get("inventory_summary", [])
    if not inventory_summary:
        return "No specific supplier or inventory data was identified for this event."

    lines = []
    for row in inventory_summary:
        days = row.get("days_of_stock_remaining")
        days_str = f"{days}" if days is not None else "no consumption tracked (effectively unlimited buffer)"
        lines.append(
            f"Supplier: {row.get('supplier_name')} | Product: {row.get('product')} | "
            f"Stock: {row.get('stock_level')} units | Daily use: {row.get('avg_daily_consumption')} | "
            f"Days remaining: {days_str} | Lead time: {row.get('reorder_lead_time')}d | "
            f"Reorder already placed: {row.get('reorder_placed')}"
        )
    return "\n".join(lines)


class DecisionAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, rag_client: RAGClient):
        super().__init__(llm_client)
        self.rag_client = rag_client

    def _fetch_rejected_options(self, query_text: str) -> str:
        results = self.rag_client.query(
            collection_name="rejections",
            query_text=query_text,
            top_k=3,
        )
        if not results:
            return "No previously rejected options found for similar situations."

        lines = []
        for i, r in enumerate(results, 1):
            meta = r["metadata"]
            lines.append(
                f"Rejected option {i}: {r['document']}\n"
                # NOTE: assumed metadata keys (action_type, rejection_reason)
                # -- verify against how case_008 / case_011 were actually
                # seeded in data/seed/cases.json and adjust if different,
                # otherwise this silently falls back to 'unknown'.
                f"  Rejected action: {meta.get('action_type', 'unknown')}\n"
                f"  Reason for rejection: {meta.get('rejection_reason', 'unknown')}"
            )
        return "\n\n".join(lines)

    def run(self, state: PipelineState) -> PipelineState:
        if state.risk_assessment is None:
            raise ValueError("DecisionAgent requires state.risk_assessment")
        if state.supplier_impact is None:
            raise ValueError("DecisionAgent requires state.supplier_impact (from Supplier Agent)")

        risk_assessment = state.risk_assessment
        supplier_impact = state.supplier_impact

        supplier_inventory_context = _format_supplier_inventory(supplier_impact)

        rag_query = (
            f"{risk_assessment.get('urgency', '')} risk mitigation for "
            f"{', '.join(risk_assessment.get('affected_products', []))} "
            f"from {', '.join(risk_assessment.get('affected_supplier_names', []))}"
        )
        rejected_context = self._fetch_rejected_options(rag_query)

        revision_context = ""
        if state.supervisor_feedback is not None:
            revision_context = (
                f"\nTHIS IS A REVISION -- iteration {state.iteration_count}. "
                f"Your previous proposal was:\n{json.dumps(state.decision_proposal, indent=2)}\n\n"
                f"The supervisor's feedback on that proposal was:\n"
                f"{json.dumps(state.supervisor_feedback, indent=2)}\n\n"
                f"You MUST address every concern raised above. Do not simply repeat the "
                f"previous proposal with cosmetic changes.\n"
            )

        prompt = DECISION_PROMPT_TEMPLATE.format(
            risk_score=risk_assessment.get("risk_score", "unknown"),
            urgency=risk_assessment.get("urgency", "unknown"),
            risk_rationale=risk_assessment.get("rationale", ""),
            supplier_inventory_context=supplier_inventory_context,
            rejected_context=rejected_context,
            revision_context=revision_context,
        )

        proposal: DecisionProposal = self.llm_client.generate(prompt, DecisionProposal)
        # Set programmatically rather than trusting the LLM's self-report --
        # we know for a fact RAG was queried above, this just records it.
        proposal.previously_rejected_options_checked = True

        state.decision_proposal = proposal.model_dump(mode="json")
        logger.info(
            "Decision proposal (iteration %d): %s on %s / %s",
            state.iteration_count,
            proposal.action_type,
            proposal.target_supplier_name,
            proposal.target_product,
        )
        return state