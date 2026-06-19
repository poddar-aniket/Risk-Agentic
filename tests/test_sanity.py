"""
Stage 0 sanity import check — run this (or `pytest`) before pushing any
branch to confirm the scaffolding still imports cleanly.
"""


def test_core_imports():
    from app.agents.base import BaseAgent  # noqa: F401
    from app.db.base_repository import BaseRepository  # noqa: F401
    from app.ingestion.base import BaseDataSource  # noqa: F401
    from app.llm.base import LLMClient  # noqa: F401
    from app.notifications.base import NotificationService  # noqa: F401
    from app.state import PipelineState  # noqa: F401

    # Day 2 additions
    from app.agents.risk_analysis import RiskAnalysisAgent  # noqa: F401
    from app.agents.schemas import RiskAssessment  # noqa: F401
    from app.db.inventory_repository import InventoryRepository  # noqa: F401
    from app.models.event import Event  # noqa: F401
    from app.models.inventory import Inventory  # noqa: F401
    from app.models.supplier import Supplier  # noqa: F401

    # Day 3 additions
    from app.agents.decision import DecisionAgent  # noqa: F401
    from app.agents.schemas import ActionType, DecisionProposal, SupplierImpact  # noqa: F401
    from app.agents.supplier import SupplierAgent  # noqa: F401

    assert True
