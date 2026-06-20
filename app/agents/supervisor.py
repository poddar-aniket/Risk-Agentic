"""
Supervisor Agent — critiques the Decision Agent's proposal and outputs a
confidence score + structured feedback.

One half of the Decision <-> Supervisor micro loop. Its confidence_score
drives the conditional edge in the LangGraph graph:
  - score >= threshold AND iterations < max  → approve, exit loop
  - score < threshold AND iterations < max   → send critique back to Decision Agent
  - iterations exhausted                     → exit regardless, flag low confidence

This agent DOES increment state.iteration_count — it's the one deciding
whether the loop continues, so it owns the counter.

Reads from state:  decision_proposal, risk_assessment, supplier_impact,
                   iteration_count (to include in critique context)
Writes to state:   supervisor_feedback, confidence_score, iteration_count (+1)
"""
import logging

from app.agents.base import BaseAgent
from app.agents.schemas import SupervisorFeedback
from app.llm.base import LLMClient
from app.rag.client import RAGClient
from app.state import PipelineState

logger = logging.getLogger(__name__)

SUPERVISOR_PROMPT_TEMPLATE = """You are a senior supply-chain risk reviewer. Your job is to critically evaluate a proposed mitigation action and decide whether it is ready for human review or needs revision.

You will score the proposal on a 1-10 confidence rubric and provide specific, actionable feedback.

CONFIDENCE RUBRIC:
1-4: Serious flaws — wrong action type for the situation, wrong scale, ignores key inventory data, or contradicts historical precedent. Must be revised.
5-6: Reasonable but improvable — vague magnitude, missing justification, or a clearly better option exists. Should be revised.
7-8: Solid proposal, well-grounded in the data, minor gaps only. Acceptable for human review.
9-10: Exemplary — specific, proportionate, grounded in all available evidence. Strong recommendation for human review.

RISK ASSESSMENT SUMMARY:
Risk score: {risk_score}/10 (urgency: {urgency})
Rationale: {risk_rationale}
Affected products: {affected_products}

SUPPLIER AND INVENTORY CONTEXT:
{inventory_context}

DECISION AGENT'S PROPOSAL (iteration {iteration_count}):
Action type: {action_type}
Target supplier: {target_supplier}
Target product: {target_product}
Justification: {justification}
Magnitude: {magnitude}
Estimated resolution: {resolution_days} days

SIMILAR HISTORICAL CASES FOR COMPARISON:
{historical_context}

EVALUATION QUESTIONS TO CONSIDER:
1. Is the action type appropriate for a risk score of {risk_score}/10?
2. Is the magnitude proportionate — neither overkill nor insufficient?
3. Does the justification explicitly reference the actual inventory numbers (days of stock, lead time)?
4. Does the proposed resolution timeline make sense given the lead time data?
5. Are there historical precedents that suggest a different approach would work better?
6. Does this proposal address the most critical product/supplier combination first?

Score the proposal using the rubric above. If confidence < 7, provide a specific revision instruction for the Decision Agent to act on in the next iteration."""

INVENTORY_CONTEXT_TEMPLATE = (
    "Supplier: {supplier_name} | Product: {product} | "
    "Stock: {stock_level} units | Daily use: {avg_daily} | "
    "Days remaining: {days} | Lead time: {lead_time}d | Reorder placed: {reorder_placed}"
)


def _format_inventory(supplier_impact: dict) -> str:
    rows = supplier_impact.get("inventory_summary", [])
    if not rows:
        return "No inventory data available."
    return "\n".join(
        INVENTORY_CONTEXT_TEMPLATE.format(
            supplier_name=r.get("supplier_name", "?"),
            product=r.get("product", "?"),
            stock_level=r.get("stock_level", "?"),
            avg_daily=r.get("avg_daily_consumption", "?"),
            days=r.get("days_of_stock_remaining", "∞"),
            lead_time=r.get("reorder_lead_time", "?"),
            reorder_placed=r.get("reorder_placed", False),
        )
        for r in rows
    )


def _format_historical(results: list[dict]) -> str:
    if not results:
        return "No similar historical cases found in the database."
    lines = []
    for i, r in enumerate(results, 1):
        meta = r.get("metadata", {})
        lines.append(
            f"Case {i}: {r.get('document', '')} | "
            f"Outcome: {meta.get('outcome', '?')} | "
            f"Duration: {meta.get('duration_days', '?')} days"
        )
    return "\n".join(lines)


class SupervisorAgent(BaseAgent):
    def __init__(self, llm_client: LLMClient, rag_client: RAGClient, confidence_threshold: float = 7.0):
        super().__init__(llm_client)
        self.rag_client = rag_client
        self.confidence_threshold = confidence_threshold

    def run(self, state: PipelineState) -> PipelineState:
        if state.decision_proposal is None:
            raise ValueError("SupervisorAgent requires state.decision_proposal")
        if state.risk_assessment is None:
            raise ValueError("SupervisorAgent requires state.risk_assessment")
        if state.supplier_impact is None:
            raise ValueError("SupervisorAgent requires state.supplier_impact")

        proposal = state.decision_proposal
        risk = state.risk_assessment
        impact = state.supplier_impact

        # query RAG for historical cases similar to this situation
        rag_query = (
            f"{risk.get('urgency', '')} disruption affecting "
            f"{', '.join(risk.get('affected_products', []))}"
        )
        historical_cases = self.rag_client.query(
            collection_name="cases",
            query_text=rag_query,
            top_k=5,
        )

        prompt = SUPERVISOR_PROMPT_TEMPLATE.format(
            risk_score=risk.get("risk_score", "?"),
            urgency=risk.get("urgency", "?"),
            risk_rationale=risk.get("rationale", ""),
            affected_products=", ".join(risk.get("affected_products", [])),
            inventory_context=_format_inventory(impact),
            iteration_count=state.iteration_count,
            action_type=proposal.get("action_type", "?"),
            target_supplier=proposal.get("target_supplier_name", "?"),
            target_product=proposal.get("target_product", "?"),
            justification=proposal.get("justification", ""),
            magnitude=proposal.get("magnitude", "?"),
            resolution_days=proposal.get("estimated_resolution_days", "?"),
            historical_context=_format_historical(historical_cases),
        )

        feedback: SupervisorFeedback = self.llm_client.generate(prompt, SupervisorFeedback)

        # supervisor owns the iteration counter
        state.iteration_count += 1
        state.confidence_score = feedback.confidence_score
        state.supervisor_feedback = feedback.model_dump(mode="json")

        logger.info(
            "Supervisor (iteration %d): confidence=%.1f, approved=%s, proportionality=%s",
            state.iteration_count,
            feedback.confidence_score,
            feedback.approved,
            feedback.proportionality_check,
        )
        return state
