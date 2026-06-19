"""
Tests for DecisionAgent.

The LLM call (self.llm_client.generate) is mocked -- it's non-deterministic
and costs real API quota, and the agent's own prompt-construction/RAG/
formatting logic is what's actually worth verifying today, not Gemini's
output quality. The RAG client is real (queries the actual seeded
"rejections" collection), since that's exactly the contract bug
(action_type) we fixed this session and want to make sure stays fixed.

Run from repo root:
    set PYTHONPATH=.
    python -m pytest tests/test_decision_agent.py -v

Assumes app/rag/seed.py has already been run (rejections collection populated
with case_008 and case_011).
"""
from unittest.mock import MagicMock

import pytest

from app.agents.decision import DecisionAgent
from app.agents.schemas import ActionType, DecisionProposal
from app.rag.client import RAGClient
from app.state import PipelineState


@pytest.fixture
def rag_client():
    return RAGClient()


@pytest.fixture
def fake_llm_client():
    """Stub LLMClient -- generate() returns a fixed, valid DecisionProposal
    regardless of prompt content. We're testing DecisionAgent's wiring
    (what it sends INTO the prompt, how it handles the response), not the
    LLM's actual reasoning quality."""
    client = MagicMock()
    client.generate.return_value = DecisionProposal(
        action_type=ActionType.PLACE_REORDER,
        target_supplier_name="Mumbai Port Logistics Co",
        target_product="rice",
        justification="Stock is at 6 days remaining against a 10-day lead time.",
        magnitude="1000 units reorder",
        estimated_resolution_days=10,
    )
    return client


@pytest.fixture
def agent(fake_llm_client, rag_client):
    return DecisionAgent(llm_client=fake_llm_client, rag_client=rag_client)


def _make_state(risk_score=7, urgency="high", affected_products=None,
                 affected_supplier_names=None, inventory_summary=None,
                 supervisor_feedback=None, decision_proposal=None,
                 iteration_count=0):
    if inventory_summary is None:
        inventory_summary = [
            {
                "product": "rice",
                "supplier_name": "Mumbai Port Logistics Co",
                "stock_level": 1200,
                "avg_daily_consumption": 200,
                "days_of_stock_remaining": 6.0,
                "reorder_lead_time": 10,
                "reorder_placed": False,
            }
        ]
    return PipelineState(
        risk_assessment={
            "risk_score": risk_score,
            "rationale": "test rationale",
            "affected_products": affected_products or ["rice"],
            "affected_supplier_names": affected_supplier_names or ["Mumbai Port Logistics Co"],
            "urgency": urgency,
            "recommended_review_within_hours": 6,
        },
        supplier_impact={
            "affected_suppliers": [],
            "affected_products": affected_products or ["rice"],
            "inventory_summary": inventory_summary,
            "total_suppliers_affected": 1,
        },
        supervisor_feedback=supervisor_feedback,
        decision_proposal=decision_proposal,
        iteration_count=iteration_count,
    )


class TestDecisionAgentBasicProposal:
    def test_run_returns_state_with_decision_proposal(self, agent):
        state = _make_state()
        result = agent.run(state)

        assert result.decision_proposal is not None
        assert result.decision_proposal["action_type"] == "place_reorder"
        assert result.decision_proposal["target_supplier_name"] == "Mumbai Port Logistics Co"

    def test_decision_proposal_is_a_dict_not_pydantic_object(self, agent):
        # Confirms DecisionAgent follows the same .model_dump(mode="json")
        # convention as every other agent (Event Extraction, Geo, Risk
        # Analysis, Supplier) -- so downstream consumers can safely call
        # .get() on state.decision_proposal.
        state = _make_state()
        result = agent.run(state)

        assert isinstance(result.decision_proposal, dict)

    def test_previously_rejected_options_checked_is_forced_true(self, agent, fake_llm_client):
        # Decision agent overrides whatever the LLM self-reports here,
        # since RAG was queried unconditionally above regardless of what
        # the LLM claims about itself.
        fake_llm_client.generate.return_value = DecisionProposal(
            action_type=ActionType.MONITOR_ONLY,
            target_supplier_name="none identified",
            target_product="none identified",
            justification="test",
            magnitude="n/a",
            estimated_resolution_days=0,
            previously_rejected_options_checked=False,  # LLM says False
        )
        state = _make_state()
        result = agent.run(state)

        assert result.decision_proposal["previously_rejected_options_checked"] is True


class TestDecisionAgentRagRejectionLookup:
    """These exercise the real RAGClient against the real seeded
    'rejections' collection -- this is the exact path that had the
    action_type bug fixed this session."""

    def test_fetch_rejected_options_does_not_crash(self, agent):
        # Before the fix, this didn't crash either (silent 'unknown'
        # fallback) -- but confirms the method still runs end-to-end
        # after removing the dead action_type lookup.
        result = agent._fetch_rejected_options("air freight escalation low margin SKUs")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_fetch_rejected_options_no_longer_prints_unknown_action(self, agent):
        # Regression guard for the bug fixed this session: the old code
        # always printed "Rejected action: unknown" because action_type
        # was never a real metadata key. After the fix this line shouldn't
        # appear at all.
        result = agent._fetch_rejected_options("air freight escalation low margin SKUs")
        assert "Rejected action: unknown" not in result

    def test_fetch_rejected_options_surfaces_real_rejection_reason(self, agent):
        # case_008's real rejection_reason mentions the 15% gross margin
        # threshold -- querying with closely related text should surface
        # it via semantic similarity.
        result = agent._fetch_rejected_options(
            "air freight escalation for low margin SKUs during port congestion"
        )
        assert "margin" in result.lower()

    def test_fetch_rejected_options_empty_rag_result_handled(self, agent, monkeypatch):
        # Force RAGClient.query to return [] and confirm the agent's
        # fallback message is used instead of crashing on empty results.
        agent.rag_client.query = MagicMock(return_value=[])
        result = agent._fetch_rejected_options("irrelevant query text")
        assert result == "No previously rejected options found for similar situations."


class TestDecisionAgentRevisionFlow:
    """Micro-loop revision path: when supervisor_feedback is set, the agent
    should build revision_context and include the previous proposal +
    feedback in the prompt sent to the LLM."""

    def test_revision_context_included_when_supervisor_feedback_present(self, agent, fake_llm_client):
        state = _make_state(
            supervisor_feedback={"confidence_score": 4.0, "concerns": ["magnitude too small"]},
            decision_proposal={
                "action_type": "place_reorder",
                "target_supplier_name": "Mumbai Port Logistics Co",
                "target_product": "rice",
                "justification": "prior justification",
                "magnitude": "500 units reorder",
                "estimated_resolution_days": 10,
                "previously_rejected_options_checked": True,
            },
            iteration_count=1,
        )
        agent.run(state)

        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "THIS IS A REVISION" in sent_prompt
        assert "magnitude too small" in sent_prompt
        assert "500 units reorder" in sent_prompt

    def test_no_revision_context_on_first_pass(self, agent, fake_llm_client):
        state = _make_state(supervisor_feedback=None, decision_proposal=None)
        agent.run(state)

        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "THIS IS A REVISION" not in sent_prompt

    def test_agent_does_not_increment_iteration_count(self, agent):
        # Per the module docstring: iteration_count belongs to Supervisor
        # Agent / the conditional edge, not DecisionAgent. This is a
        # contract guard -- if DecisionAgent starts incrementing this too,
        # the micro-loop will double-count iterations once Supervisor
        # Agent is built.
        state = _make_state(iteration_count=2)
        result = agent.run(state)

        assert result.iteration_count == 2


class TestDecisionAgentRequiredStateFields:
    def test_missing_risk_assessment_raises(self, agent):
        state = _make_state()
        state.risk_assessment = None
        with pytest.raises(ValueError, match="risk_assessment"):
            agent.run(state)

    def test_missing_supplier_impact_raises(self, agent):
        state = _make_state()
        state.supplier_impact = None
        with pytest.raises(ValueError, match="supplier_impact"):
            agent.run(state)


class TestDecisionAgentNoSpecificTarget:
    def test_empty_inventory_summary_still_produces_valid_proposal(self, agent, fake_llm_client):
        # Per the prompt template: if no specific supplier/product was
        # identified, the LLM is instructed to use monitor_only with
        # "none identified" -- this just confirms the agent plumbs an
        # empty inventory_summary through without crashing on formatting.
        fake_llm_client.generate.return_value = DecisionProposal(
            action_type=ActionType.MONITOR_ONLY,
            target_supplier_name="none identified",
            target_product="none identified",
            justification="No specific supplier or inventory data was identified.",
            magnitude="n/a",
            estimated_resolution_days=0,
        )
        state = _make_state(inventory_summary=[])
        result = agent.run(state)

        assert result.decision_proposal["action_type"] == "monitor_only"

        sent_prompt = fake_llm_client.generate.call_args[0][0]
        assert "No specific supplier or inventory data was identified for this event." in sent_prompt