"""
Tests for SupplierAgent and DecisionAgent.
- SupplierAgent: no LLM call, pure DB retrieval — test that it correctly
  maps regions to suppliers and builds the inventory summary.
- DecisionAgent: uses FakeLLMClient + FakeRAGClient — test that it reads
  risk + supplier impact correctly, checks RAG for rejections, and writes
  decision_proposal to state.
"""
from typing import Type, TypeVar

import pytest
from pydantic import BaseModel
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.decision import DecisionAgent
from app.agents.schemas import ActionType, DecisionProposal
from app.agents.supplier import SupplierAgent
from app.db.session import Base
from app.llm.base import LLMClient
from app.models.inventory import Inventory
from app.models.supplier import Supplier
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
    def __init__(self, past_cases=None, rejected=None):
        self.past_cases = past_cases or []
        self.rejected = rejected or []
        self.queries: list[str] = []

    def query(self, collection_name: str, query_text: str, top_k: int = 5) -> list[dict]:
        self.queries.append(query_text)
        if collection_name == "rejections":
            return self.rejected
        return self.past_cases

    def add(self, collection_name, documents, metadatas, ids):
        pass


# ---- shared DB fixture ----

@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()

    s1 = Supplier(name="Ramesh Agro Suppliers", region="Tamil Nadu",
                  products_supplied="rice,wheat", status="active")
    s2 = Supplier(name="Maharashtra Grain Co.", region="Maharashtra",
                  products_supplied="wheat,sugar", status="active")
    db.add_all([s1, s2])
    db.flush()

    db.add(Inventory(supplier_id=s1.id, product="rice",
                     stock_level=400, avg_daily_consumption=80,
                     reorder_lead_time=14, reorder_threshold=560, reorder_placed=False))
    db.add(Inventory(supplier_id=s1.id, product="wheat",
                     stock_level=700, avg_daily_consumption=50,
                     reorder_lead_time=14, reorder_threshold=350, reorder_placed=False))
    db.add(Inventory(supplier_id=s2.id, product="wheat",
                     stock_level=1500, avg_daily_consumption=90,
                     reorder_lead_time=10, reorder_threshold=450, reorder_placed=False))
    db.commit()
    yield db
    db.close()


# ---- SupplierAgent tests ----

def test_supplier_agent_maps_region_to_correct_suppliers(db_session):
    agent = SupplierAgent(llm_client=FakeLLMClient(None), db=db_session)
    state = PipelineState(
        affected_regions={
            "primary_regions": ["Tamil Nadu"],
            "description": "Tamil Nadu coastline affected.",
        },
        risk_assessment={
            "affected_supplier_names": [],
            "affected_products": [],
            "risk_score": 7,
            "urgency": "high",
            "rationale": "",
            "recommended_review_within_hours": 4,
        },
    )
    result = agent.run(state)

    assert result.supplier_impact is not None
    names = [s["name"] for s in result.supplier_impact["affected_suppliers"]]
    assert "Ramesh Agro Suppliers" in names
    assert "Maharashtra Grain Co." not in names


def test_supplier_agent_builds_inventory_summary(db_session):
    agent = SupplierAgent(llm_client=FakeLLMClient(None), db=db_session)
    state = PipelineState(
        affected_regions={"primary_regions": ["Tamil Nadu"], "description": ""},
        risk_assessment={
            "affected_supplier_names": [],
            "affected_products": [],
            "risk_score": 7,
            "urgency": "high",
            "rationale": "",
            "recommended_review_within_hours": 4,
        },
    )
    result = agent.run(state)

    products = result.supplier_impact["affected_products"]
    assert "rice" in products
    assert "wheat" in products

    rice_row = next(r for r in result.supplier_impact["inventory_summary"] if r["product"] == "rice")
    assert rice_row["days_of_stock_remaining"] == 5.0


def test_supplier_agent_requires_affected_regions(db_session):
    agent = SupplierAgent(llm_client=FakeLLMClient(None), db=db_session)
    with pytest.raises(ValueError, match="affected_regions"):
        agent.run(PipelineState(
            risk_assessment={
                "affected_supplier_names": [],
                "affected_products": [],
                "risk_score": 5,
                "urgency": "medium",
                "rationale": "",
                "recommended_review_within_hours": 12,
            }
        ))


def test_supplier_agent_handles_no_suppliers_found(db_session):
    agent = SupplierAgent(llm_client=FakeLLMClient(None), db=db_session)
    state = PipelineState(
        affected_regions={"primary_regions": ["Ladakh"], "description": ""},
        risk_assessment={
            "affected_supplier_names": [],
            "affected_products": [],
            "risk_score": 2,
            "urgency": "low",
            "rationale": "",
            "recommended_review_within_hours": 24,
        },
    )
    result = agent.run(state)
    assert result.supplier_impact["total_suppliers_affected"] == 0
    assert result.supplier_impact["affected_products"] == []


# ---- DecisionAgent tests ----
# Aniket's DecisionAgent takes only (llm_client, rag_client) — no db.

@pytest.fixture
def canned_proposal():
    return DecisionProposal(
        action_type=ActionType.PLACE_REORDER,
        target_supplier_name="Ramesh Agro Suppliers",
        target_product="rice",
        justification="Rice stock will run out in 5 days, before the 14-day lead time. Immediate reorder required.",
        magnitude="500 units urgent reorder",
        estimated_resolution_days=14,
        previously_rejected_options_checked=True,
    )


@pytest.fixture
def full_state():
    return PipelineState(
        risk_assessment={
            "risk_score": 8,
            "rationale": "Rice stock critically low.",
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
                 "supplier_id": 1, "stock_level": 400, "avg_daily_consumption": 80,
                 "days_of_stock_remaining": 5.0, "reorder_lead_time": 14,
                 "reorder_threshold": 560, "reorder_placed": False},
            ],
            "total_suppliers_affected": 1,
        },
    )


def test_decision_agent_populates_decision_proposal(canned_proposal, full_state):
    fake_llm = FakeLLMClient(canned_proposal)
    agent = DecisionAgent(llm_client=fake_llm, rag_client=FakeRAGClient())

    result = agent.run(full_state)

    assert result.decision_proposal is not None
    assert result.decision_proposal["action_type"] == "place_reorder"
    assert result.decision_proposal["target_product"] == "rice"
    assert result.decision_proposal["previously_rejected_options_checked"] is True


def test_decision_agent_prompt_includes_inventory_numbers(canned_proposal, full_state):
    fake_llm = FakeLLMClient(canned_proposal)
    agent = DecisionAgent(llm_client=fake_llm, rag_client=FakeRAGClient())
    agent.run(full_state)

    assert "5.0" in fake_llm.last_prompt
    assert "Ramesh Agro Suppliers" in fake_llm.last_prompt
    assert "rice" in fake_llm.last_prompt


def test_decision_agent_includes_rejected_options_in_prompt(canned_proposal, full_state):
    rejected = [{"document": "expedite_shipment for rice from Ramesh",
                 "metadata": {"rejection_reason": "No faster transport available"}}]
    fake_rag = FakeRAGClient(rejected=rejected)
    fake_llm = FakeLLMClient(canned_proposal)
    agent = DecisionAgent(llm_client=fake_llm, rag_client=fake_rag)
    agent.run(full_state)

    assert "No faster transport available" in fake_llm.last_prompt


def test_decision_agent_requires_risk_assessment(canned_proposal):
    agent = DecisionAgent(llm_client=FakeLLMClient(canned_proposal),
                          rag_client=FakeRAGClient())
    with pytest.raises(ValueError, match="risk_assessment"):
        agent.run(PipelineState(supplier_impact={"affected_products": []}))


def test_decision_agent_requires_supplier_impact(canned_proposal):
    agent = DecisionAgent(llm_client=FakeLLMClient(canned_proposal),
                          rag_client=FakeRAGClient())
    with pytest.raises(ValueError, match="supplier_impact"):
        agent.run(PipelineState(risk_assessment={"risk_score": 7, "urgency": "high",
                                                  "rationale": "", "affected_products": []}))