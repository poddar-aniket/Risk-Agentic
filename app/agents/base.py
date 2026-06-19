"""
BaseAgent — abstract base for all six agents (Event Extraction, Geo, Risk
Analysis, Supplier, Decision, Supervisor). LangGraph calls agent.run()
polymorphically as each node, so every concrete agent only needs to implement
run(); the graph doesn't need to know which agent it's calling.
"""
from abc import ABC, abstractmethod

from app.llm.base import LLMClient
from app.state import PipelineState


class BaseAgent(ABC):
    def __init__(self, llm_client: LLMClient):
        # Dependency Inversion: agents depend on the LLMClient interface,
        # not a concrete provider. Swapping Gemini -> OpenAI later means
        # changing what gets injected here, not touching agent code.
        self.llm_client = llm_client

    @abstractmethod
    def run(self, state: PipelineState) -> PipelineState:
        """
        Read whatever this agent needs from `state`, do its reasoning
        (typically one self.llm_client.generate(...) call against a
        structured Pydantic schema), write the result back onto the
        relevant field of `state`, and return it.
        """
        raise NotImplementedError
