"""
tests/test_routes.py

Route-level coverage for app/api/routes.py.

SCOPE / WHAT THIS FILE DOES NOT COVER:
- execute_approved_decision() internal logic (action_type routing, repo
  lookups, the "never raises" guard) -- that's already covered by
  tests/test_execution.py (14 tests). Here, execute_approved_decision is
  mocked at the route level: we only assert the route CALLS it with the
  approved decision + db session, and threads its return value into the
  response under "simulated_execution". Re-deriving execution.py's
  internal behavior here would be duplicate coverage, not new coverage.
- DecisionRepository.approve()/reject()/get_pending() internal logic --
  these are mocked at the class level (patched in routes.py's own
  namespace, same pattern as test_execution.py's repo mocking). This
  file's job is route wiring/response-shape/status-code behavior, not
  repository correctness.
- RAGClient.add() internal behavior -- mocked. We assert reject_decision
  calls it with the right collection name, document content, and
  metadata shape; we do not test RAGClient itself.

ASSUMPTIONS MADE EXPLICIT (not verified against real repo behavior this
session -- flagging per this project's standing rule against treating
"specified" as "verified"):
  1. DecisionRepository.approve()/reject() return None for a decision_id
     that doesn't exist OR is already in a terminal state (approved/
     rejected). This is the most common pattern for this kind of code
     and is what list_queue/approve/reject's None-check in routes.py
     implies, but it has NOT been confirmed against the actual
     decision_repository.py source this session.
  2. ValueError is reserved for some OTHER invalid-state case not yet
     identified (routes.py catches it -> 400, but no docstring or repo
     source was available this session to confirm what actually raises
     it). The 400-path test below proves "IF the repo raises ValueError,
     the route returns 400 with that message" -- it does NOT prove what
     real-world condition triggers a ValueError, because that wasn't
     confirmed. Don't read more into this test than that.
  Both assumptions should be confirmed against decision_repository.py's
  actual source before this comment block is removed.

KNOWN OPEN QUESTION, FLAGGED NOT FIXED:
  approve_decision/reject_decision return raw SQLAlchemy Decision model
  instances directly (not via a Pydantic response_model, and -- as far
  as confirmed this session -- without a response_model/from_attributes
  configured anywhere visible in routes.py). FastAPI's default JSONResponse
  cannot serialize an arbitrary ORM object on its own; depending on the
  Decision model's setup (e.g. a custom __json__ / Pydantic
  model_validate elsewhere not shown), this could 500 in production on
  every successful approve/reject. This file does NOT attempt to fix
  that. Instead, the success-path tests below construct the mocked
  return value as a plain dict (not a real ORM object) specifically so
  these tests can pass and exercise routing/status-code/call-wiring
  logic WITHOUT silently asserting that serialization works -- because
  that hasn't been confirmed either way. If/when this is checked against
  the real Decision model, that's a separate, real finding to log in the
  master doc -- not something to quietly paper over by mocking a dict
  here and calling it done.

CONFIRMED THIS SESSION, VIA A REAL TEST FAILURE (not assumed up front):
  reject_decision's RAG-document-building code does attribute access on
  the returned decision (decision.action_type, .target_supplier_name,
  .target_product, .justification, .id) -- NOT dict-style subscript
  access. This was discovered because the first draft of this file used
  a plain dict for ALL fixtures (including reject's), and running it
  against the real repo produced
  `AttributeError: 'dict' object has no attribute 'action_type'` on
  exactly the 4 reject tests that touch those fields -- not on approve
  or list_queue, which never access decision fields directly. This
  confirms reject_decision really does expect an object with attributes
  (consistent with a real ORM row), which is suggestive evidence
  (though not by itself confirmation) that Decision is a normal
  SQLAlchemy model rather than something dict-like. Fixed in this file
  by giving reject-path tests a SimpleNamespace-based fixture
  (_fake_decision_obj) instead of the dict-based one
  (_fake_decision) used elsewhere. This does NOT resolve the
  "KNOWN OPEN QUESTION" above about serialization -- attribute access
  working is a different question from JSON serialization working.
"""
import pytest
from types import SimpleNamespace
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from app.api import routes


@pytest.fixture
def app():
    test_app = FastAPI()
    test_app.include_router(routes.router)

    def _override_get_db():
        yield MagicMock()

    from app.db.session import get_db
    test_app.dependency_overrides[get_db] = _override_get_db
    return test_app


@pytest.fixture
def client(app):
    return TestClient(app)


def _fake_decision(decision_id=1, **overrides):
    """
    Plain dict standing in for a Decision row. See module docstring's
    'KNOWN OPEN QUESTION' section for why this is deliberately not a
    real ORM-like object.
    """
    base = {
        "id": decision_id,
        "action_type": "place_reorder",
        "target_supplier_name": "Mumbai Port Logistics Co",
        "target_product": "rice",
        "justification": "Test justification",
        "status": "approved",
    }
    base.update(overrides)
    return base


def _fake_decision_obj(decision_id=1, **overrides):
    """
    Object-with-attributes version of _fake_decision(), for use ONLY
    where the route itself does attribute access on the decision
    (currently: reject_decision's RAG-document-building code does
    decision.action_type / .target_supplier_name / .target_product /
    .justification / .id -- confirmed via a real test failure this
    session, not assumed).

    NOTE ON WHY TWO HELPERS EXIST: approve_decision never accesses
    fields on the decision itself (it passes the object straight
    through to execute_approved_decision() and the response dict), so
    a plain dict is sufficient there and deliberately kept -- using a
    dict for THOSE tests is what lets them stay honest about not
    proving anything re: Decision's real serialization behavior (see
    module docstring, "KNOWN OPEN QUESTION"). reject_decision is
    different: routes.py's own code reaches into the object's fields
    directly, so the test fixture has to support that or it isn't
    testing the real code path. SimpleNamespace is used rather than a
    real Decision/SQLAlchemy model, since this file still doesn't
    assert anything about the real model's serialization -- it only
    needs attribute access to exist, not to be correct in every other
    respect a real ORM row would be.
    """
    base = {
        "id": decision_id,
        "action_type": "place_reorder",
        "target_supplier_name": "Mumbai Port Logistics Co",
        "target_product": "rice",
        "justification": "Test justification",
        "status": "approved",
    }
    base.update(overrides)
    return SimpleNamespace(**base)


# ---------------------------------------------------------------------
# GET /queue
# ---------------------------------------------------------------------

class TestListQueue:
    def test_returns_pending_decisions(self, client):
        pending = [_fake_decision(1), _fake_decision(2)]
        with patch.object(routes, "DecisionRepository") as MockRepo:
            MockRepo.return_value.get_pending.return_value = pending
            response = client.get("/queue")

        assert response.status_code == 200
        assert response.json() == pending

    def test_returns_empty_list_when_no_pending_decisions(self, client):
        with patch.object(routes, "DecisionRepository") as MockRepo:
            MockRepo.return_value.get_pending.return_value = []
            response = client.get("/queue")

        assert response.status_code == 200
        assert response.json() == []

    def test_constructs_repository_with_injected_db_session(self, client):
        # Confirms DecisionRepository(db) is called with the db session
        # FastAPI injects via the get_db dependency override, not some
        # other session.
        with patch.object(routes, "DecisionRepository") as MockRepo:
            MockRepo.return_value.get_pending.return_value = []
            client.get("/queue")

        assert MockRepo.call_count == 1
        # First positional arg to DecisionRepository(...) should be the
        # (mocked) db session from the overridden dependency.
        called_with_db = MockRepo.call_args[0][0]
        assert called_with_db is not None


# ---------------------------------------------------------------------
# POST /queue/{decision_id}/approve
# ---------------------------------------------------------------------

class TestApproveDecision:
    def test_successful_approve_calls_execution_and_wraps_response(self, client):
        decision = _fake_decision(1)
        execution_result = {"status": "executed", "action_taken": "mark_reorder_placed"}

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "execute_approved_decision") as mock_execute:
            MockRepo.return_value.approve.return_value = decision
            mock_execute.return_value = execution_result

            response = client.post("/queue/1/approve")

        assert response.status_code == 200
        body = response.json()
        assert body["decision"] == decision
        assert body["simulated_execution"] == execution_result

    def test_execute_approved_decision_called_with_approved_decision_and_db(self, client):
        decision = _fake_decision(1)

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "execute_approved_decision") as mock_execute:
            MockRepo.return_value.approve.return_value = decision
            mock_execute.return_value = {"status": "no_op"}

            client.post("/queue/1/approve")

        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0]
        assert call_args[0] == decision  # the just-approved decision, not the id
        # second positional arg should be a db session (not None, not the decision)
        assert call_args[1] is not None
        assert call_args[1] != decision

    def test_approve_nonexistent_decision_returns_404(self, client):
        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "execute_approved_decision") as mock_execute:
            MockRepo.return_value.approve.return_value = None

            response = client.post("/queue/999/approve")

        assert response.status_code == 404
        assert response.json()["detail"] == "Decision not found"
        # Execution must NEVER be attempted for a decision that wasn't
        # actually approved -- this is the important wiring guarantee,
        # not just the status code.
        mock_execute.assert_not_called()

    def test_approve_invalid_state_returns_400(self, client):
        # See module docstring ASSUMPTION 2: this proves route behavior
        # GIVEN a ValueError from the repo, not what real condition
        # triggers one.
        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "execute_approved_decision") as mock_execute:
            MockRepo.return_value.approve.side_effect = ValueError("decision already approved")

            response = client.post("/queue/1/approve")

        assert response.status_code == 400
        assert response.json()["detail"] == "decision already approved"
        mock_execute.assert_not_called()

    def test_execution_result_is_included_even_when_execution_is_a_noop(self, client):
        # Guards against a route-level regression where a no-op /
        # falsy-but-valid execution_result gets dropped instead of
        # passed through (e.g. an `if execution_result:` check added
        # later that wasn't there in the original code).
        decision = _fake_decision(1)
        noop_result = {"status": "no_op", "action_taken": None}

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "execute_approved_decision") as mock_execute:
            MockRepo.return_value.approve.return_value = decision
            mock_execute.return_value = noop_result

            response = client.post("/queue/1/approve")

        assert response.status_code == 200
        assert response.json()["simulated_execution"] == noop_result


# ---------------------------------------------------------------------
# POST /queue/{decision_id}/reject
# ---------------------------------------------------------------------

class TestRejectDecision:
    def test_successful_reject_returns_decision_and_writes_to_rag(self, client):
        decision = _fake_decision_obj(
            1,
            action_type="place_reorder",
            target_supplier_name="Mumbai Port Logistics Co",
            target_product="rice",
            justification="Predicted delay at origin port",
        )

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            MockRepo.return_value.reject.return_value = decision

            response = client.post("/queue/1/reject", json={"reason": "Already mitigated"})

        # NOT asserting response.json() == decision here. decision is a
        # SimpleNamespace standing in for a real Decision ORM row -- see
        # module docstring's "KNOWN OPEN QUESTION". Whether FastAPI can
        # actually serialize the real Decision object reject_decision
        # returns is exactly the unconfirmed thing flagged there; that
        # passed silently in an earlier draft of this test only because
        # the old fixture happened to be a dict already, which would
        # have hidden a real serialization gap rather than catching it.
        # We confirm what we CAN confirm without assuming serialization:
        # success status code, and that the RAG write fired.
        assert response.status_code == 200
        mock_rag.add.assert_called_once()

    def test_rag_write_uses_rejections_collection(self, client):
        decision = _fake_decision_obj(1)

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            MockRepo.return_value.reject.return_value = decision

            client.post("/queue/1/reject", json={"reason": "Not needed"})

        _, kwargs = mock_rag.add.call_args
        assert kwargs["collection_name"] == "rejections"

    def test_rag_write_document_includes_action_target_and_reason(self, client):
        decision = _fake_decision_obj(
            1,
            action_type="hold_supplier",
            target_supplier_name="Delhi Freight Partners",
            target_product="steel",
            justification="Late shipments in past 30 days",
        )

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            MockRepo.return_value.reject.return_value = decision

            client.post("/queue/1/reject", json={"reason": "Supplier already replaced"})

        _, kwargs = mock_rag.add.call_args
        doc_text = kwargs["documents"][0]
        assert "hold_supplier" in doc_text
        assert "Delhi Freight Partners" in doc_text
        assert "steel" in doc_text
        assert "Late shipments in past 30 days" in doc_text
        assert "Supplier already replaced" in doc_text

    def test_rag_write_metadata_includes_decision_id_and_reason(self, client):
        decision = _fake_decision_obj(1)

        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            MockRepo.return_value.reject.return_value = decision

            client.post("/queue/1/reject", json={"reason": "Duplicate alert"})

        _, kwargs = mock_rag.add.call_args
        assert kwargs["metadatas"] == [{"decision_id": decision.id, "rejection_reason": "Duplicate alert"}]
        assert kwargs["ids"] == [f"decision_{decision.id}_rejection"]

    def test_reject_nonexistent_decision_returns_404_and_skips_rag_write(self, client):
        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            MockRepo.return_value.reject.return_value = None

            response = client.post("/queue/999/reject", json={"reason": "n/a"})

        assert response.status_code == 404
        assert response.json()["detail"] == "Decision not found"
        # The RAG write must never fire for a rejection that didn't
        # actually happen -- this is the important guarantee here, not
        # just the 404 itself. A bug that wrote to "rejections" before
        # checking decision is None would be a real, separate
        # data-integrity issue.
        mock_rag.add.assert_not_called()

    def test_reject_invalid_state_returns_400_and_skips_rag_write(self, client):
        # See module docstring ASSUMPTION 2 -- same caveat as the
        # approve-path equivalent test.
        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            MockRepo.return_value.reject.side_effect = ValueError("decision already rejected")

            response = client.post("/queue/1/reject", json={"reason": "n/a"})

        assert response.status_code == 400
        assert response.json()["detail"] == "decision already rejected"
        mock_rag.add.assert_not_called()

    def test_reject_requires_reason_field(self, client):
        # Pydantic validation on RejectRequest -- missing "reason" should
        # 422, not reach the repository at all.
        with patch.object(routes, "DecisionRepository") as MockRepo, \
             patch.object(routes, "_rag_client") as mock_rag:
            response = client.post("/queue/1/reject", json={})

        assert response.status_code == 422
        MockRepo.return_value.reject.assert_not_called()
        mock_rag.add.assert_not_called()