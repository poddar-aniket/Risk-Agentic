"""
Geo Agent.

TODO (Day 2 — owner: poddar-aniket):
- LLM reasons about which regions/transport routes/infrastructure are
  affected by structured_event. No hardcoded distance/radius rules — the
  reasoning itself should be in the prompt, not in code.
- Define an AffectedRegions Pydantic schema and write the prompt.
"""
from app.agents.base import BaseAgent
from app.state import PipelineState


class GeoAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        raise NotImplementedError("Geo Agent — build on Day 2")
