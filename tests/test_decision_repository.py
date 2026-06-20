# tests/test_decision_repository.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.db.decision_repository import DecisionRepository
from app.models.decision import Decision


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    yield session
    session.close()


def _sample_decision():
    # status defaults to "pending" via the column default -- not set explicitly
    return Decision(
        action_type="reorder",
        target="rice",
        justification="5 days of stock remaining, 14-day lead time.",
        confidence_score=6.5,
    )


def test_pending_queue_lists_pending_decisions(db_session):
    repo = DecisionRepository(db_session)
    repo.add(_sample_decision())
    repo.add(_sample_decision())
    pending = repo.get_pending()
    assert len(pending) == 2
    assert all(d.status == "pending" for d in pending)


def test_approve_sets_status(db_session):
    repo = DecisionRepository(db_session)
    decision = repo.add(_sample_decision())
    approved = repo.approve(decision.id)
    assert approved.status == "approved"


def test_approve_returns_none_for_missing_id(db_session):
    repo = DecisionRepository(db_session)
    assert repo.approve(999) is None


def test_reject_stores_reason_and_sets_status(db_session):
    repo = DecisionRepository(db_session)
    decision = repo.add(_sample_decision())
    rejected = repo.reject(decision.id, reason="Already on-hold for unrelated issue")
    assert rejected.status == "rejected"
    assert rejected.rejection_reason == "Already on-hold for unrelated issue"


def test_reject_returns_none_for_missing_id(db_session):
    repo = DecisionRepository(db_session)
    assert repo.reject(999, reason="n/a") is None


def test_get_pending_excludes_approved_and_rejected(db_session):
    repo = DecisionRepository(db_session)
    pending = repo.add(_sample_decision())
    approved = repo.add(_sample_decision())
    repo.approve(approved.id)
    rejected = repo.add(_sample_decision())
    repo.reject(rejected.id, reason="no")

    result = repo.get_pending()
    ids = {d.id for d in result}
    assert pending.id in ids
    assert approved.id not in ids
    assert rejected.id not in ids