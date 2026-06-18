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

    assert True
