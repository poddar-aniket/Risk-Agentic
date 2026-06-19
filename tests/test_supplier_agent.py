"""
Tests for SupplierAgent — run against real seeded DB data
(data/seed/seed_supply_data.py), not mocks, since the whole point of this
agent is precise structured lookup against real rows.

Run from repo root:
    set PYTHONPATH=.
    python -m pytest tests/test_supplier_agent.py -v

Assumes seed_supply_data.py has already been run against the dev SQLite DB.
"""
import pytest

from app.agents.supplier import SupplierAgent
from app.db.session import SessionLocal
from app.state import PipelineState


@pytest.fixture
def db():
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture
def agent(db):
    # llm_client is unused by SupplierAgent (see module docstring in
    # supplier.py) but required by BaseAgent's constructor — None is fine
    # here since run() never touches self.llm_client.
    return SupplierAgent(llm_client=None, db=db)


def _make_state(affected_supplier_names=None, primary_regions=None,
                 risk_score=6, urgency="medium"):
    """Builds a minimal PipelineState with just the fields SupplierAgent
    actually reads: state.affected_regions and state.risk_assessment.
    Both must be dicts (confirmed Day 3: Geo Agent and Risk Analysis Agent
    both write via .model_dump(mode="json") before assigning to state)."""
    return PipelineState(
        affected_regions={
            "primary_regions": primary_regions or [],
            "description": "test region payload",
        },
        risk_assessment={
            "risk_score": risk_score,
            "rationale": "test rationale",
            "affected_products": [],
            "affected_supplier_names": affected_supplier_names or [],
            "urgency": urgency,
            "recommended_review_within_hours": 24,
        },
    )


class TestSupplierAgentNamedSupplierMatch:
    """Primary signal: suppliers named explicitly by Risk Analysis Agent."""

    def test_exact_name_match_resolves_supplier(self, agent):
        state = _make_state(affected_supplier_names=["Chennai Textile Exports"])
        result = agent.run(state)

        impact = result.supplier_impact
        names = [s["name"] for s in impact["affected_suppliers"]]
        assert "Chennai Textile Exports" in names
        assert impact["total_suppliers_affected"] == 1

    def test_named_supplier_inventory_is_attached(self, agent):
        state = _make_state(affected_supplier_names=["Mumbai Port Logistics Co"])
        result = agent.run(state)

        impact = result.supplier_impact
        products = {row["product"] for row in impact["inventory_summary"]}
        assert products == {"rice", "wheat"}

    def test_low_stock_supplier_days_remaining_is_correct(self, agent):
        # Seeded: Mumbai Port Logistics Co / rice — stock_level=1200,
        # avg_daily_consumption=200 -> 6.0 days remaining, near its
        # reorder_threshold of 1000.
        state = _make_state(affected_supplier_names=["Mumbai Port Logistics Co"])
        result = agent.run(state)

        rice_row = next(
            r for r in result.supplier_impact["inventory_summary"]
            if r["product"] == "rice"
        )
        assert rice_row["days_of_stock_remaining"] == pytest.approx(6.0, abs=0.1)

    def test_below_threshold_supplier_flagged_with_low_days(self, agent):
        # Seeded: Kolkata Jute Mills / jute — stock_level=300,
        # avg_daily_consumption=60 -> 5.0 days remaining, already below
        # its reorder_threshold of 500.
        state = _make_state(affected_supplier_names=["Kolkata Jute Mills"])
        result = agent.run(state)

        jute_row = next(
            r for r in result.supplier_impact["inventory_summary"]
            if r["product"] == "jute"
        )
        assert jute_row["days_of_stock_remaining"] == pytest.approx(5.0, abs=0.1)

    def test_fuzzy_name_still_resolves(self, agent):
        # get_by_name is a LIKE-based fuzzy match (confirmed Day 3 doc note:
        # "fuzzy name match, not filtered to active"). A partial name from
        # an LLM call should still resolve to the real seeded supplier.
        state = _make_state(affected_supplier_names=["Jute Mills"])
        result = agent.run(state)

        names = [s["name"] for s in result.supplier_impact["affected_suppliers"]]
        assert "Kolkata Jute Mills" in names

    def test_unknown_supplier_name_resolves_to_nothing_by_itself(self, agent):
        # A name that matches no seeded supplier and no region should fall
        # through to the "no candidates found" branch.
        state = _make_state(
            affected_supplier_names=["Totally Fictional Supplier Ltd"],
            primary_regions=[],
        )
        result = agent.run(state)

        assert result.supplier_impact["total_suppliers_affected"] == 0
        assert result.supplier_impact["affected_suppliers"] == []


class TestSupplierAgentRegionMatch:
    """Supplementary signal: suppliers found via region, not explicitly named."""

    def test_region_match_finds_unnamed_supplier(self, agent):
        state = _make_state(primary_regions=["Tamil Nadu"])
        result = agent.run(state)

        names = [s["name"] for s in result.supplier_impact["affected_suppliers"]]
        assert "Chennai Textile Exports" in names

    def test_region_with_multiple_suppliers(self, agent):
        # Only one seeded supplier per region currently, but this guards
        # against silently dropping suppliers if more share a region later.
        state = _make_state(primary_regions=["Maharashtra"])
        result = agent.run(state)

        names = [s["name"] for s in result.supplier_impact["affected_suppliers"]]
        assert "Mumbai Port Logistics Co" in names

    def test_unknown_region_with_no_named_suppliers_returns_empty(self, agent):
        state = _make_state(primary_regions=["Kerala"])  # not seeded
        result = agent.run(state)

        assert result.supplier_impact["total_suppliers_affected"] == 0


class TestSupplierAgentDeduplication:
    def test_same_supplier_via_name_and_region_not_duplicated(self, agent):
        # Chennai Textile Exports matched both by exact name AND by region
        # "Tamil Nadu" -- candidates dict is keyed by id, so this must
        # collapse to a single entry, not two.
        state = _make_state(
            affected_supplier_names=["Chennai Textile Exports"],
            primary_regions=["Tamil Nadu"],
        )
        result = agent.run(state)

        assert result.supplier_impact["total_suppliers_affected"] == 1

    def test_multiple_distinct_suppliers_across_name_and_region(self, agent):
        state = _make_state(
            affected_supplier_names=["Chennai Textile Exports"],
            primary_regions=["West Bengal"],  # Kolkata Jute Mills
        )
        result = agent.run(state)

        names = {s["name"] for s in result.supplier_impact["affected_suppliers"]}
        assert names == {"Chennai Textile Exports", "Kolkata Jute Mills"}
        assert result.supplier_impact["total_suppliers_affected"] == 2


class TestSupplierAgentNoMatchPath:
    def test_no_candidates_returns_valid_empty_supplier_impact(self, agent):
        state = _make_state(affected_supplier_names=[], primary_regions=[])
        result = agent.run(state)

        impact = result.supplier_impact
        # Confirms SupplierImpact() with no constructor args is valid
        # Pydantic (every field has a default) and survives model_dump.
        assert impact["affected_suppliers"] == []
        assert impact["affected_products"] == []
        assert impact["inventory_summary"] == []
        assert impact["total_suppliers_affected"] == 0


class TestSupplierAgentRequiredStateFields:
    def test_missing_affected_regions_raises(self, agent):
        state = PipelineState(
            affected_regions=None,
            risk_assessment={"affected_supplier_names": []},
        )
        with pytest.raises(ValueError, match="affected_regions"):
            agent.run(state)

    def test_missing_risk_assessment_raises(self, agent):
        state = PipelineState(
            affected_regions={"primary_regions": []},
            risk_assessment=None,
        )
        with pytest.raises(ValueError, match="risk_assessment"):
            agent.run(state)