"""
Decision Agent.

TODO (Day 3 — owner: ash119821):
- Propose mitigation(s) grounded in risk_assessment, inventory data, and RAG.
- Check RAG for previously-rejected options before proposing, so rejected
  ideas aren't repeated for similar future situations.
- Output is structured: action type, target supplier/product, justification,
  magnitude.
"""
from app.agents.base import BaseAgent
from app.state import PipelineState


class DecisionAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        raise NotImplementedError("Decision Agent — build on Day 3")
