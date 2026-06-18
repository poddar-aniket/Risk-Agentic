"""
Event Extraction Agent.

TODO (Day 1 — owner: ash119821):
- Define a structured Event Pydantic schema: type, location, severity, timeframe.
  This schema is the contract the rest of the pipeline depends on (Geo Agent,
  Risk Analysis Agent, etc. all consume it downstream) — decide field types
  deliberately rather than patching them on Day 2.
- Write the extraction prompt (raw article text -> Event).
- Implement run() using self.llm_client.generate(prompt, EventSchema).
"""
from app.agents.base import BaseAgent
from app.state import PipelineState


class EventExtractionAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        raise NotImplementedError("Event Extraction Agent — build on Day 1")
