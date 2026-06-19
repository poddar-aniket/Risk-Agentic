"""
Tests for RiskAnalysisAgent. Uses:
- FakeLLMClient (canned RiskAssessment, no real Gemini call)
- FakeRAGClient (canned results, no real ChromaDB)
- In-memory SQLite with real supplier/inventory rows

This verifies the agent's wiring: does it read event + regions correctly,
fetch suppliers by region, format context, call generate() with the right
schema, and write the result back to state?
"""
from typing import Type, TypeVar

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.risk_analysis import RiskAnalysisAgent
from app.agents.schemas import RiskAssessment
from app.db.session import Base
from app.llm.base import LLMClient
from app.models.inventory import Inventory
from app.models.supplier import Supplier
from app.rag.client import RAGClient
from app.state import PipelineState

T = TypeVar("T", bound=BaseModel)

# ---- test doubles ----

class FakeLLMClient(LLMClient):
    def __init__(self, canned: RiskAssessment):
        self.canned = canned
        self.last_prompt: str | None = None

    def generate(self, prompt: str, output_schema: Type[T]) -> T:
        self.last_prompt = prompt
        assert output_schema is RiskAssessment
        return self.canned


class FakeRAGClient(RAGClient):
    def query(self, query_text: str, top_k: int = 5) -> list[dict]:
        return [
            {
                "document": "2023 Tamil Nadu flooding closed Chennai port for 6 days",
                "metadata": {"outcome": "delayed", "duration_days": "6"},
            }
        ]

    def add(self, documents, metadatas, ids):
        pass


# ---- fixtures ----

@pytest.fixture
def db_session():
    """In-memory SQLite session with seeded supplier + inventory rows."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    supplier = Supplier(
        name="Ramesh Agro Suppliers",
        region="Tamil Nadu",
        products_supplied="rice,wheat",
        status="active",
    )
    db.add(supplier)
    db.flush()

    db.add(Inventory(
        supplier_id=supplier.id,
        product="rice",
        stock_level=400,
        avg_daily_consumption=80,
        reorder_lead_time=14,
        reorder_threshold=560,
        reorder_placed=False,
    ))
    db.add(Inventory(
        supplier_id=supplier.id,
        product="wheat",
        stock_level=200,
        avg_daily_consumption=50,
        reorder_lead_time=14,
        reorder_threshold=350,
        reorder_placed=False,
    ))
    db.commit()
    yield db
    db.close()


@pytest.fixture
def canned_assessment():
    return RiskAssessment(
        risk_score=8,
        rationale="Tamil Nadu supplier Ramesh Agro has only 5 days of rice stock remaining. Historical flooding cases lasted 6 days on average.",
        affected_products=["rice", "wheat"],
        affected_supplier_names=["Ramesh Agro Suppliers"],
        urgency="high",
        recommended_review_within_hours=4,
    )


# ---- tests ----

def test_risk_analysis_agent_populates_risk_assessment(db_session, canned_assessment):
    fake_llm = FakeLLMClient(canned_assessment)
    fake_rag = FakeRAGClient()
    agent = RiskAnalysisAgent(llm_client=fake_llm, db=db_session, rag_client=fake_rag)

    state = PipelineState(
        structured_event={
            "is_relevant": True,
            "event_type": "natural_disaster",
            "locations": ["Chennai", "Tamil Nadu"],
            "severity": 7,
            "timeframe_status": "ongoing",
            "estimated_duration_days": 5,
            "summary": "Cyclone Mira has closed Chennai port for 3 days.",
        },
        affected_regions={
            "primary_regions": ["Tamil Nadu"],
            "description": "Tamil Nadu coastline and Chennai port area severely affected.",
        },
    )

    result = agent.run(state)

    assert result.risk_assessment is not None
    assert result.risk_assessment["risk_score"] == 8
    assert result.risk_assessment["urgency"] == "high"
    assert "rice" in result.risk_assessment["affected_products"]
    assert "Ramesh Agro Suppliers" in result.risk_assessment["affected_supplier_names"]


def test_risk_analysis_prompt_includes_supplier_data(db_session, canned_assessment):
    """Verify that the prompt actually contains the supplier's real inventory numbers."""
    fake_llm = FakeLLMClient(canned_assessment)
    agent = RiskAnalysisAgent(llm_client=fake_llm, db=db_session, rag_client=FakeRAGClient())

    state = PipelineState(
        structured_event={
            "event_type": "natural_disaster",
            "locations": ["Tamil Nadu"],
            "severity": 7,
            "timeframe_status": "ongoing",
            "estimated_duration_days": 5,
            "summary": "Flooding in Tamil Nadu.",
        },
        affected_regions={
            "primary_regions": ["Tamil Nadu"],
            "description": "Tamil Nadu affected.",
        },
    )
    agent.run(state)

    assert "Ramesh Agro Suppliers" in fake_llm.last_prompt
    assert "rice" in fake_llm.last_prompt
    assert "5.0" in fake_llm.last_prompt  # days of stock remaining for rice (400/80)


def test_risk_analysis_agent_raises_without_event(db_session, canned_assessment):
    agent = RiskAnalysisAgent(
        llm_client=FakeLLMClient(canned_assessment),
        db=db_session,
        rag_client=FakeRAGClient(),
    )
    state = PipelineState(affected_regions={"primary_regions": ["Tamil Nadu"], "description": ""})
    with pytest.raises(ValueError, match="structured_event"):
        agent.run(state)


def test_risk_analysis_agent_raises_without_regions(db_session, canned_assessment):
    agent = RiskAnalysisAgent(
        llm_client=FakeLLMClient(canned_assessment),
        db=db_session,
        rag_client=FakeRAGClient(),
    )
    state = PipelineState(
        structured_event={"event_type": "natural_disaster", "locations": [], "severity": 5,
                          "timeframe_status": "ongoing", "summary": "test"}
    )
    with pytest.raises(ValueError, match="affected_regions"):
        agent.run(state)
