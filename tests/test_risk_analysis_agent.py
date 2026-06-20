"""
Tests for RiskAnalysisAgent.

The LLM call (self.llm_client.generate) is mocked, same rationale as
test_decision_agent.py: the agent's own prompt-construction and formatting
logic is what's worth verifying today, not Gemini's output quality. The DB
session is real (seeded dev SQLite via seed_supply_data.py) and the RAG
client is real (queries the actual seeded "past_events" collection) --
this is exactly the path that had two live bugs fixed this session (RAG
call signature, and _format_rag_context reading metadata keys that never
existed), and we want regression guards for both.

Run from repo root:
    set PYTHONPATH=.
    python -m pytest tests/test_risk_analysis_agent.py -v

Assumes seed_supply_data.py and app/rag/seed.py have both already been run.
"""
from unittest.mock import MagicMock

import pytest

from app.agents.risk_analysis import (
    RiskAnalysisAgent,
    _format_rag_context,
    _format_supplier_inventory,
)
from app.agents.schemas import RiskAssessment
from app.db.inventory_repository import InventoryRepository
from app.db.session import SessionLocal
from app.rag.client import RAGClient
from app.state import PipelineState


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def rag_client():
    return RAGClient()


@pytest.fixture
def fake_llm_client():
    """Stub LLMClient -- generate() returns a fixed, valid RiskAssessment
    regardless of prompt content. We're testing the agent's wiring (what
    it sends INTO the prompt), not the LLM's actual reasoning quality."""
    client = MagicMock()
    client.generate.return_value = RiskAssessment(
        risk_score=7,
        rationale="test rationale",
        affected_products=["rice"],
        affected_supplier_names=["Mumbai Port Logistics Co"],
        urgency="high",
        recommended_review_within_hours=6,
    )
    return client


@pytest.fixture
def agent(fake_llm_client, db, rag_client):
    return RiskAnalysisAgent(llm_client=fake_llm_client, db=db, rag_client=rag_client)


def _make_state(event_type="transport_disruption", locations=None,
                 severity=8, timeframe_status="ongoing",
                 estimated_duration_days=10,
                 summary="Port congestion disrupting shipments.",
                 primary_regions=None):
    return PipelineState(
        structured_event={
            "is_relevant": True,
            "event_type": event_type,
            "locations": locations or ["Maharashtra"],
            "severity": severity,
            "timeframe_status": timeframe_status,
            "estimated_duration_days": estimated_duration_days,
            "summary": summary,
        },
        affected_regions={
            "primary_regions": primary_regions or ["Maharashtra"],
            "description": "test affected regions payload",
        },
    )


class TestRiskAnalysisAgentBasicFlow:
    def test_run_returns_state_with_risk_assessment(self, agent):
        result = agent.run(_make_state())
        assert result.risk_assessment is not None
        assert result.risk_assessment["risk_score"] == 7
        assert result.risk_assessment["urgency"] == "high"

    def test_risk_assessment_is_a_dict_not_pydantic_object(self, agent):
        # Confirms RiskAnalysisAgent follows the same .model_dump(mode="json")
        # convention as every other agent in the pipeline.
        result = agent.run(_make_state())
        assert isinstance(result.risk_assessment, dict)


class TestRiskAnalysisAgentSupplierInventoryContext:
    def test_seeded_supplier_in_region_appears_in_prompt(self, agent, fake_llm_client):
        # Maharashtra -> Mumbai Port Logistics Co (seeded).
        agent.run(_make_state(primary_regions=["Maharashtra"]))
        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "Mumbai Port Logistics Co" in sent_prompt
        assert "rice" in sent_prompt

    def test_low_stock_days_remaining_shown_in_prompt(self, agent, fake_llm_client):
        # Seeded: Mumbai Port Logistics Co / rice -- 1200 stock / 200 daily
        # = 6.0 days remaining, exactly the number the rubric needs.
        agent.run(_make_state(primary_regions=["Maharashtra"]))
        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "Days remaining: 6.0" in sent_prompt

    def test_unseeded_region_falls_back_to_no_suppliers_message(self, agent, fake_llm_client):
        agent.run(_make_state(primary_regions=["Kerala"]))  # not seeded
        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "No suppliers found in the directly affected regions." in sent_prompt

    def test_format_supplier_inventory_directly_with_no_suppliers(self, db):
        result = _format_supplier_inventory([], InventoryRepository(db))
        assert result == "No suppliers found in the directly affected regions."


class TestRiskAnalysisAgentRagContext:
    """Regression guards for the two bugs fixed this session: the RAG
    query call signature, and _format_rag_context reading metadata keys
    ('outcome', 'duration_days') that never existed in the seeded data."""

    def test_format_rag_context_reads_real_metadata_keys(self):
        # Mirrors the actual seeded shape from seed_past_events():
        # days_to_resolve / historical_delay_days, not the old wrong keys.
        fake_results = [{
            "document": "Suez Canal Blockage. Container ship ran aground.",
            "metadata": {"id": "case_001", "event_type": "transport_disruption",
                         "days_to_resolve": 6, "historical_delay_days": 14},
            "distance": 0.1,
        }]
        result = _format_rag_context(fake_results)
        assert "Days to resolve: 6" in result
        assert "Historical delay: 14 days" in result
        # The old bug silently printed '?' for both -- guard against regressing.
        assert "Days to resolve: ?" not in result
        assert "Historical delay: ? days" not in result

    def test_format_rag_context_empty_results(self):
        assert _format_rag_context([]) == "No similar historical cases found in the database."

    def test_rag_query_uses_correct_collection_and_query_text(self, agent):
        # Regression guard: the original bug called
        # rag_client.query(rag_query, top_k=5) -- missing collection_name
        # and query_text as proper args, which raised TypeError on first run.
        agent.rag_client.query = MagicMock(return_value=[])
        agent.run(_make_state(event_type="transport_disruption", locations=["Mumbai"]))
        agent.rag_client.query.assert_called_once_with(
            collection_name="past_events",
            query_text="transport_disruption disruption in Mumbai",
            top_k=5,
        )

    def test_real_rag_query_against_seeded_data_does_not_crash(self, rag_client):
        results = rag_client.query(
            collection_name="past_events",
            query_text="transport_disruption disruption in Suez Canal, Egypt",
            top_k=5,
        )
        assert isinstance(results, list)
        assert len(results) > 0

    def test_rag_context_in_full_prompt_has_real_numbers_not_placeholders(self, agent, fake_llm_client):
        state = _make_state(
            event_type="transport_disruption",
            locations=["Suez Canal, Egypt"],
            summary="A container ship ran aground blocking a major shipping canal.",
        )
        agent.run(state)
        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "Days to resolve: ?" not in sent_prompt
        assert "Historical delay: ? days" not in sent_prompt


class TestRiskAnalysisAgentRequiredStateFields:
    def test_missing_structured_event_raises(self, agent):
        state = _make_state()
        state.structured_event = None
        with pytest.raises(ValueError, match="structured_event"):
            agent.run(state)

    def test_missing_affected_regions_raises(self, agent):
        state = _make_state()
        state.affected_regions = None
        with pytest.raises(ValueError, match="affected_regions"):
            agent.run(state)