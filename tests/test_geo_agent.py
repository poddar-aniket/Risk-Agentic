"""
Tests for GeoAgent (app/agents/geo.py).

REPLACES the old tests/test_geo_agent.py, which was a standalone script
(run_test()/get_mock_state(), `if __name__ == "__main__"`) requiring a
live GEMINI_API_KEY and a populated ChromaDB. Two problems with that
script, found while writing this file:

1. It was never actually collected by pytest in the first place. Its only
   function is `run_test()` -- pytest's default discovery only picks up
   functions starting with `test`, and "run_test" doesn't match that
   pattern. Running `pytest tests/test_geo_agent.py` would report 0 items
   collected from it, silently. It only ever ran via
   `python tests/test_geo_agent.py` directly.
2. Even run directly, it has zero assertions -- it prints output and
   unconditionally prints "Geo Agent test passed." at the end regardless
   of what came back. It would print "passed" against a completely wrong
   geographic_spread or an empty primary_regions list just as readily as
   a correct one.

This file replaces it with real, automated, mocked-LLM pytest tests (same
pattern as tests/test_decision_agent.py's fake_llm_client) so Geo Agent
coverage exists without needing live credentials, and so it actually
fails when the agent's output contract breaks.

IMPORTANT FINDING from writing this file -- see
TestGeoAgentRagQueryTextBug below: the old script's get_mock_state() used
keys 'title', 'location' (singular), 'description', 'published_at' for
structured_event. The real Event schema (app/agents/schemas.py) has NO
such fields -- it produces 'locations' (plural, list) and 'summary' via
Event.model_dump(mode='json'). geo.py's run() builds its RAG query_text
from the old field names, which don't exist on the real Event payload, so
in the actual pipeline query_text is always just the bare event_type with
extra whitespace -- the RAG historical-case lookup is blind to WHERE the
event happened. The old script's mock data happened to use the same wrong
field names as the buggy code, so it never could have caught this: mock
and bug were internally consistent with each other, just not with the
real upstream schema. One test below is written against the REAL Event
shape and currently FAILS, which is the point -- it's flagging a real,
live bug, not a broken test. See that class's docstring for the fix.

Run from repo root:
    set PYTHONPATH=.
    python -m pytest tests/test_geo_agent.py -v
"""
from unittest.mock import MagicMock

import pytest

from app.agents.geo import GeoAgent, GeoImpactSchema
from app.state import PipelineState


def _real_event(locations=None,
                 summary="Heavy rain is expected to disrupt the Chennai port corridor for several days.",
                 event_type="natural_disaster", severity=7,
                 timeframe_status="ongoing", estimated_duration_days=4):
    """Shaped exactly like Event.model_dump(mode='json') from
    app/agents/schemas.py: is_relevant, event_type, locations (list,
    plural), severity, timeframe_status, estimated_duration_days, summary.
    Deliberately does NOT include 'title' / 'location' (singular) /
    'description' / 'published_at' -- the real Event schema has no such
    fields, and Event Extraction Agent never writes them onto
    state.structured_event. The old test_geo_agent.py's mock used those
    legacy field names; this one matches what the real pipeline actually
    produces."""
    return {
        "is_relevant": True,
        "event_type": event_type,
        "locations": locations if locations is not None else ["Chennai", "Tamil Nadu"],
        "severity": severity,
        "timeframe_status": timeframe_status,
        "estimated_duration_days": estimated_duration_days,
        "summary": summary,
    }


@pytest.fixture
def fake_llm_client():
    """Stub LLMClient -- generate() returns a fixed, valid
    GeoImpactSchema regardless of prompt content. These tests verify
    GeoAgent's wiring (what goes into the prompt/RAG query, how the
    response is written back to state), not Gemini's actual reasoning
    quality."""
    client = MagicMock()
    client.generate.return_value = GeoImpactSchema(
        primary_regions=["Chennai", "Tamil Nadu"],
        affected_routes=["NH45", "Chennai Port"],
        infrastructure_at_risk=["Chennai Port"],
        geographic_spread="regional",
        estimated_duration_days=4,
        description="Test description of impact.",
        reasoning="Test step-by-step reasoning.",
    )
    return client


@pytest.fixture
def fake_rag_client():
    client = MagicMock()
    client.query.return_value = []
    return client


@pytest.fixture
def agent(fake_llm_client, fake_rag_client):
    return GeoAgent(llm_client=fake_llm_client, rag_client=fake_rag_client)


def _sent_prompt(fake_llm_client):
    return fake_llm_client.generate.call_args.kwargs["prompt"]


class TestGeoAgentRequiredState:
    def test_missing_structured_event_raises(self, agent):
        state = PipelineState(structured_event=None)
        with pytest.raises(ValueError, match="structured_event"):
            agent.run(state)


class TestGeoAgentBasicRun:
    def test_run_writes_affected_regions_as_dict(self, agent):
        state = PipelineState(structured_event=_real_event())
        result = agent.run(state)

        assert isinstance(result.affected_regions, dict)
        assert result.affected_regions["geographic_spread"] == "regional"
        assert result.affected_regions["primary_regions"] == ["Chennai", "Tamil Nadu"]

    def test_run_calls_llm_with_geo_impact_schema(self, agent, fake_llm_client):
        state = PipelineState(structured_event=_real_event())
        agent.run(state)

        assert fake_llm_client.generate.call_args.kwargs["output_schema"] is GeoImpactSchema


class TestGeoAgentPromptContent:
    def test_prompt_includes_real_locations_field(self, agent, fake_llm_client):
        state = PipelineState(
            structured_event=_real_event(locations=["Visakhapatnam", "Andhra Pradesh"])
        )
        agent.run(state)

        prompt = _sent_prompt(fake_llm_client)
        assert "Visakhapatnam" in prompt
        assert "Andhra Pradesh" in prompt

    def test_prompt_includes_real_summary_field(self, agent, fake_llm_client):
        state = PipelineState(
            structured_event=_real_event(summary="A specific test summary about port closures.")
        )
        agent.run(state)

        prompt = _sent_prompt(fake_llm_client)
        assert "A specific test summary about port closures." in prompt

    def test_prompt_retains_region_specificity_guidance(self, agent, fake_llm_client):
        """Regression guard for the original Day 3 Geo Agent bugfix
        ('missing region-specificity guidance'). If a future edit to
        _build_prompt silently drops this instruction -- the exact
        failure mode this project's own process notes flag repeatedly,
        a specified/intended edit not actually landing -- this test
        catches it instead of it surfacing during a demo."""
        state = PipelineState(structured_event=_real_event())
        agent.run(state)

        prompt = _sent_prompt(fake_llm_client)
        assert "MOST SPECIFIC level" in prompt


class TestGeoAgentRagSimilarCasesFormatting:
    def test_no_similar_cases_found_uses_fallback_text(self, agent, fake_llm_client, fake_rag_client):
        fake_rag_client.query.return_value = []
        state = PipelineState(structured_event=_real_event())
        agent.run(state)

        assert "No similar historical cases found." in _sent_prompt(fake_llm_client)

    def test_similar_cases_are_formatted_into_prompt(self, agent, fake_llm_client, fake_rag_client):
        fake_rag_client.query.return_value = [
            {
                "document": "Test historical case description.",
                "metadata": {
                    "event_type": "natural_disaster",
                    "location": "Tamil Nadu",
                    "severity": 6,
                    "historical_delay_days": 3,
                    "days_to_resolve": 7,
                },
            }
        ]
        state = PipelineState(structured_event=_real_event())
        agent.run(state)

        prompt = _sent_prompt(fake_llm_client)
        assert "Test historical case description." in prompt
        assert "Historical delay: 3 days" in prompt


class TestGeoAgentRagQueryTextBug:
    """THIS TEST CURRENTLY FAILS against geo.py as it stands. That's the
    point -- it's reporting a real bug found while writing this coverage,
    not a broken test that needs adjusting to pass.

    GeoAgent.run() builds query_text (the text sent to RAGClient.query
    for historical-case retrieval) like this:

        query_text = (
            f"{event_dict.get('title', '')} "
            f"{event_dict.get('event_type', '')} "
            f"{event_dict.get('location', '')} "
            f"{event_dict.get('description', '')}"
        )

    'title', 'location' (singular), and 'description' are not fields on
    the real Event schema (app/agents/schemas.py) -- it has 'locations'
    (plural, list) and 'summary'. Since Event Extraction Agent writes
    state.structured_event via Event.model_dump(mode='json'), in the real
    pipeline those three .get() calls always return '', and query_text
    collapses to just " {event_type} " with extra whitespace -- the RAG
    similarity search backing the historical-duration/description
    grounding is effectively blind to WHERE the event happened, only
    WHAT TYPE it is. This directly undercuts the architecture's stated
    goal of grounding Geo Agent's estimates in similar historical cases.

    SUGGESTED FIX in geo.py's run():
        query_text = (
            f"{event_dict.get('event_type', '')} "
            f"{', '.join(event_dict.get('locations', []))} "
            f"{event_dict.get('summary', '')}"
        )

    Once fixed, this test should pass without modification.
    """

    def test_rag_query_text_includes_actual_location_and_summary(
        self, agent, fake_llm_client, fake_rag_client
    ):
        state = PipelineState(
            structured_event=_real_event(
                locations=["Visakhapatnam", "Andhra Pradesh"],
                summary="Cyclone landfall expected near Bapatla with heavy port disruption.",
            )
        )
        agent.run(state)

        query_text = fake_rag_client.query.call_args.kwargs["query_text"]
        assert "Visakhapatnam" in query_text or "Andhra Pradesh" in query_text
        assert "Bapatla" in query_text or "Cyclone landfall" in query_text