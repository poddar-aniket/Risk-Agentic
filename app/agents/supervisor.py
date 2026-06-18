"""
Supervisor Agent.

TODO (Day 3 — owner: poddar-aniket):
- Critique the Decision Agent's proposal: proportionality to risk score,
  internal consistency, gaps, historical precedent via RAG.
- Output structured feedback + a confidence score (LLM-rubric-based judgment,
  not a formula).
- This agent's confidence_score + iteration_count drive the conditional edge
  in the LangGraph micro loop (Decision <-> Supervisor, up to 5 iterations).
"""
from app.agents.base import BaseAgent
from app.state import PipelineState


class SupervisorAgent(BaseAgent):
    def run(self, state: PipelineState) -> PipelineState:
        raise NotImplementedError("Supervisor Agent — build on Day 3")
