"""
Tests EventExtractionAgent's wiring (does it read raw_article correctly, call
generate() with the right schema, and write the result back to state) without
hitting the real Gemini API. Use this to confirm the plumbing works before
burning real API quota on manual testing.
"""
from typing import Type, TypeVar

from pydantic import BaseModel

from app.agents.event_extraction import EventExtractionAgent
from app.agents.schemas import Event, EventType, TimeframeStatus
from app.llm.base import LLMClient
from app.state import PipelineState

T = TypeVar("T", bound=BaseModel)


class FakeLLMClient(LLMClient):
    """Returns a canned Event instead of calling a real model."""

    def __init__(self, canned_response: Event):
        self.canned_response = canned_response
        self.last_prompt: str | None = None

    def generate(self, prompt: str, output_schema: Type[T]) -> T:
        self.last_prompt = prompt
        assert output_schema is Event
        return self.canned_response


def test_event_extraction_agent_populates_structured_event():
    canned_event = Event(
        is_relevant=True,
        event_type=EventType.NATURAL_DISASTER,
        locations=["Chennai", "Tamil Nadu"],
        severity=7,
        timeframe_status=TimeframeStatus.ONGOING,
        estimated_duration_days=5,
        summary="Heavy flooding has shut down the Chennai port for several days.",
    )
    fake_client = FakeLLMClient(canned_event)
    agent = EventExtractionAgent(llm_client=fake_client)

    state = PipelineState(
        raw_article={
            "source": "newsdata",
            "title": "Chennai port closed amid severe flooding",
            "content": "Heavy rains have flooded the Chennai port area, halting operations...",
        }
    )

    result_state = agent.run(state)

    assert result_state.structured_event is not None
    assert result_state.structured_event["event_type"] == "natural_disaster"
    assert result_state.structured_event["severity"] == 7
    assert "Chennai" in result_state.structured_event["locations"]
    assert "Chennai port closed" in fake_client.last_prompt


def test_event_extraction_agent_requires_raw_article():
    fake_client = FakeLLMClient(
        Event(
            is_relevant=False,
            event_type=EventType.OTHER,
            severity=1,
            timeframe_status=TimeframeStatus.RESOLVED,
            summary="n/a",
        )
    )
    agent = EventExtractionAgent(llm_client=fake_client)
    state = PipelineState()  # raw_article is None

    try:
        agent.run(state)
        assert False, "expected ValueError when raw_article is missing"
    except ValueError:
        pass
