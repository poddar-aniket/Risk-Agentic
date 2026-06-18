"""
Supplier Agent.

TODO (Day 3 — owner: ash119821):
- Map affected_regions to specific suppliers/products using the DB repos
  (SupplierRepository, etc.) built on Day 2.
"""
from app.agents.base import BaseAgent
from app.state import PipelineState


class SupplierAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        raise NotImplementedError("Supplier Agent — build on Day 3")
