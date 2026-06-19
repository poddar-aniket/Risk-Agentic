"""
Risk Analysis Agent.

TODO (Day 2 — owner: ash119821):
- Combine structured_event, affected_regions, supplier/inventory data, weather
  data, and RAG-retrieved similar past cases to produce a risk score (1-10)
  + written rationale.
- Needs poddar-aniket's RAGClient (app/rag/client.py) — agree on its interface
  by 11am Day 2 so this isn't blocked mid-day.
- Prompt must include a rubric anchored to real numeric context: % of supply
  through the affected route, days-of-inventory buffer, historical delay
  durations pulled from RAG. The score comes from the LLM's rubric-based
  judgment, not a formula in code.
"""
from app.agents.base import BaseAgent
from app.state import PipelineState


class RiskAnalysisAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        raise NotImplementedError("Risk Analysis Agent — build on Day 2")
