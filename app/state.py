"""
PipelineState — threaded through the LangGraph StateGraph, accumulating each
agent's output as it flows through the pipeline.

Each field below is currently a loose `dict | None` placeholder. As each agent
gets built (Stages 1-3), replace the corresponding field's type with that
agent's real Pydantic output schema (e.g. structured_event: Optional[Event]).
Keeping them loose for now means Stage 0 imports cleanly without forcing any
agent's schema design decisions before that agent's day arrives.
"""
from typing import Optional
from pydantic import BaseModel


class PipelineState(BaseModel):
    # --- inputs ---
    raw_article: Optional[dict] = None             # from a BaseDataSource adapter (Day 1)

    # --- agent outputs, populated in pipeline order ---
    structured_event: Optional[dict] = None         # Event Extraction Agent (Day 1, owner: ash119821)
    affected_regions: Optional[dict] = None         # Geo Agent (Day 2, owner: poddar-aniket)
    risk_assessment: Optional[dict] = None          # Risk Analysis Agent (Day 2, owner: ash119821)
    supplier_impact: Optional[dict] = None          # Supplier Agent (Day 3, owner: ash119821)
    decision_proposal: Optional[dict] = None        # Decision Agent (Day 3, owner: ash119821)
    supervisor_feedback: Optional[dict] = None      # Supervisor Agent (Day 3, owner: poddar-aniket)

    # --- micro loop bookkeeping ---
    confidence_score: Optional[float] = None
    iteration_count: int = 0

    # --- HITL framing, set once the micro loop ends ---
    hitl_framing: Optional[str] = None              # "high_confidence" | "low_confidence"
