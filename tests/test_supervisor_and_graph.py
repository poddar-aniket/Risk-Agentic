"""
Tests for SupervisorAgent and the LangGraph graph.

SupervisorAgent: verify it reads proposal + risk + inventory correctly,
queries RAG with the right collection name, writes supervisor_feedback and
confidence_score to state, and increments iteration_count.

Graph routing: verify micro_loop_router returns the right next node under
all three conditions (high confidence → exit, low confidence + iterations
remaining → loop, iterations exhausted → exit).
"""
from typing import Type, TypeVar

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.schemas import (
    ActionType,
    DecisionProposal,
    RiskAssessment,
    SupervisorFeedback,
)
from app.agents.supervisor import SupervisorAgent
from app.db.session import Base
from app.llm.base import LLMClient
from app.models.inventory import Inventory
from app.models.supplier import Supplier
from app.orchestration.graph import micro_loop_router
from app.rag.client import RAGClient
from app.state import PipelineState

T = TypeVar("T", bound=BaseModel)


# ---- test doubles ----

class FakeLLMClient(LLMClient):
    def __init__(self, canned: BaseModel):
        self.canned = canned
        self.last_prompt: str | None = None

    def generate(self, prompt: str, output_schema: Type[T]) -> T:
        self.last_prompt = prompt
        return self.canned


class FakeRAGClient(RAGClient):
    def __init__(self, results=None):
        self.results = results or []
        self.calls: list[dict] = []

    def query(self, collection_name: str, query_text: str, top_k: int = 5) -> list[dict]:
        self.calls.append({"collection": collection_name, "query": query_text})
        return self.results

    def add(self, collection_name, documents, metadatas, ids):
        pass


# ---- shared fixtures ----

@pytest.fixture
def full_state():
    return PipelineState(
        risk_assessment={
            "risk_score": 8,
            "rationale": "Rice stock critically low at 5 days, below 14-day lead time.",
            "affected_products": ["rice", "wheat"],
            "affected_supplier_names": ["Ramesh Agro Suppliers"],
            "urgency": "high",
            "recommended_review_within_hours": 4,
        },
        supplier_impact={
            "affected_suppliers": [{"id": 1, "name": "Ramesh Agro Suppliers",
                                    "region": "Tamil Nadu", "products_supplied": "rice,wheat",
                                    "status": "active"}],
            "affected_products": ["rice", "wheat"],
            "inventory_summary": [
                {"product": "rice", "supplier_name": "Ramesh Agro Suppliers",
                 "stock_level": 400, "avg_daily_consumption": 80,
                 "days_of_stock_remaining": 5.0, "reorder_lead_time": 14,
                 "reorder_placed": False},
            ],
            "total_suppliers_affected": 1,
        },
        decision_proposal={
            "action_type": "place_reorder",
            "target_supplier_name": "Ramesh Agro Suppliers",
            "target_product": "rice",
            "justification": "5 days of rice stock remaining, 14-day lead time — reorder immediately.",
            "magnitude": "1000 units urgent reorder",
            "estimated_resolution_days": 14,
            "previously_rejected_options_checked": True,
        },
        iteration_count=0,
    )


@pytest.fixture
def canned_feedback_approved():
    return SupervisorFeedback(
        confidence_score=8.5,
        approved=True,
        critique="Proposal is well-grounded. References 5-day stock and 14-day lead time directly.",
        suggested_revision=None,
        proportionality_check="proportionate",
    )


@pytest.fixture
def canned_feedback_rejected():
    return SupervisorFeedback(
        confidence_score=4.0,
        approved=False,
        critique="Magnitude is too low. 1000 units only covers 12.5 days at current consumption.",
        suggested_revision="Increase reorder to at least 1200 units to cover lead time plus 1-week buffer.",
        proportionality_check="insufficient",
    )


# ---- SupervisorAgent tests ----

def test_supervisor_writes_feedback_and_confidence(full_state, canned_feedback_approved):
    fake_llm = FakeLLMClient(canned_feedback_approved)
    agent = SupervisorAgent(llm_client=fake_llm, rag_client=FakeRAGClient())

    result = agent.run(full_state)

    assert result.supervisor_feedback is not None
    assert result.confidence_score == 8.5
    assert result.supervisor_feedback["approved"] is True
    assert result.supervisor_feedback["proportionality_check"] == "proportionate"


def test_supervisor_increments_iteration_count(full_state, canned_feedback_approved):
    agent = SupervisorAgent(llm_client=FakeLLMClient(canned_feedback_approved),
                            rag_client=FakeRAGClient())
    assert full_state.iteration_count == 0
    result = agent.run(full_state)
    assert result.iteration_count == 1


def test_supervisor_queries_cases_collection(full_state, canned_feedback_approved):
    fake_rag = FakeRAGClient()
    agent = SupervisorAgent(llm_client=FakeLLMClient(canned_feedback_approved),
                            rag_client=fake_rag)
    agent.run(full_state)

    assert len(fake_rag.calls) == 1
    assert fake_rag.calls[0]["collection"] == "cases"


def test_supervisor_prompt_includes_proposal_details(full_state, canned_feedback_approved):
    fake_llm = FakeLLMClient(canned_feedback_approved)
    agent = SupervisorAgent(llm_client=fake_llm, rag_client=FakeRAGClient())
    agent.run(full_state)

    assert "place_reorder" in fake_llm.last_prompt
    assert "Ramesh Agro Suppliers" in fake_llm.last_prompt
    assert "1000 units" in fake_llm.last_prompt
    assert "5.0" in fake_llm.last_prompt  # days of stock from inventory


def test_supervisor_raises_without_decision_proposal(full_state, canned_feedback_approved):
    full_state.decision_proposal = None
    agent = SupervisorAgent(llm_client=FakeLLMClient(canned_feedback_approved),
                            rag_client=FakeRAGClient())
    with pytest.raises(ValueError, match="decision_proposal"):
        agent.run(full_state)


def test_supervisor_raises_without_risk_assessment(full_state, canned_feedback_approved):
    full_state.risk_assessment = None
    agent = SupervisorAgent(llm_client=FakeLLMClient(canned_feedback_approved),
                            rag_client=FakeRAGClient())
    with pytest.raises(ValueError, match="risk_assessment"):
        agent.run(full_state)


# ---- micro_loop_router tests ----

def test_router_exits_when_confidence_meets_threshold():
    state = PipelineState(confidence_score=7.5, iteration_count=1)
    result = micro_loop_router(state, confidence_threshold=7.0, max_iterations=5)
    assert result == "hitl_framing"


def test_router_loops_when_confidence_below_threshold():
    state = PipelineState(confidence_score=4.0, iteration_count=1)
    result = micro_loop_router(state, confidence_threshold=7.0, max_iterations=5)
    assert result == "decision"


def test_router_exits_when_iterations_exhausted():
    state = PipelineState(confidence_score=3.0, iteration_count=5)
    result = micro_loop_router(state, confidence_threshold=7.0, max_iterations=5)
    assert result == "hitl_framing"


def test_router_exits_exactly_at_threshold():
    state = PipelineState(confidence_score=7.0, iteration_count=2)
    result = micro_loop_router(state, confidence_threshold=7.0, max_iterations=5)
    assert result == "hitl_framing"


def test_router_loops_on_first_iteration_low_confidence():
    state = PipelineState(confidence_score=5.0, iteration_count=1)
    result = micro_loop_router(state, confidence_threshold=7.0, max_iterations=5)
    assert result == "decision"
