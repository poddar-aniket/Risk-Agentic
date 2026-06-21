"""
tests/test_scheduler.py

Coverage for app/orchestration/scheduler.py: _get_next_event(),
run_pipeline_once(), start_scheduler().

CONFIRMED THIS SESSION, VIA DIRECT FILE READS (not assumed):
  - PipelineState (app/state.py) is a Pydantic BaseModel with every
    field Optional[dict] = None (or a bare default), and no
    `model_config = ConfigDict(extra="forbid")` visible. Pydantic v2's
    default `extra` behavior is "ignore" -- meaning PipelineState(**result)
    will NOT raise on unexpected/extra keys in result; it silently drops
    anything not already declared as a field. This is real, slightly
    risky behavior (a typo'd key anywhere upstream in the graph would
    vanish silently rather than error) and is covered by a dedicated
    test below rather than just asserted in this comment.
  - BaseDataSource.fetch_events() (app/ingestion/base.py) returns
    list[RawArticle], where RawArticle has fields: source, title,
    content, url (optional), published_at (optional). This confirms
    _get_next_event()'s raw_article["title"]/["content"] access (after
    .model_dump(mode="json")) lines up with real field names -- no
    mismatch found here, unlike the routes.py dict-vs-attribute issue
    found in a prior pass on this project.

SCOPE / WHAT THIS FILE MOCKS AND WHY:
  - SessionLocal, load_config, create_llm_client, RAGClient, all six
    agent classes, build_graph, ApprovalQueueRepository -- ALL mocked.
    run_pipeline_once() is a wiring/orchestration function: its job is
    "construct these things in this order, call graph.invoke(), persist
    the result correctly." None of the agents' or graph's OWN internal
    logic is this file's concern -- those have (or should have) their
    own test coverage elsewhere. Re-deriving agent/graph correctness
    here would be duplicate coverage, not new coverage, same reasoning
    as routes.py's tests mocking execute_approved_decision() rather
    than re-testing execution.py's internals.
  - SourceFactory.create_all -- mocked in _get_next_event's tests via
    fake BaseDataSource subclasses returning real RawArticle instances,
    so the contract proven by app/ingestion/base.py is actually
    exercised, not just assumed.
  - BackgroundScheduler, run_pipeline_once -- both mocked for
    start_scheduler()'s tests. See module-level note below for why.

START_SCHEDULER MOCKING DECISION (made by Claude, confirmed acceptable
by the user when asked -- "your call"):
  start_scheduler() calls run_pipeline_once() unconditionally and
  immediately at the very end of the function, in addition to
  scheduling it on an interval. An integration-style test (real
  BackgroundScheduler, real run_pipeline_once) would mean every test
  run actually executes a full pipeline cycle -- real or mocked LLM
  calls cascading through six agents, real DB writes -- just to check
  scheduling wiring. That's slow, expensive, and duplicates coverage
  run_pipeline_once()'s own tests (below) already provide. So:
  BackgroundScheduler and run_pipeline_once are both mocked here; these
  tests only prove "does start_scheduler() call add_job with the right
  trigger/interval, does it call run_pipeline_once exactly once on
  startup, does it return the scheduler instance" -- not anything about
  what running the job for real would do.

NOT COVERED HERE, FLAGGED NOT IGNORED:
  - The dead-code duplicate `return None` at the end of the original
    _get_next_event() (two near-identical "no candidates" log+return
    blocks, the second unreachable) was found and fixed directly in
    scheduler.py earlier this session, BEFORE this test file was
    written. These tests are written against the cleaned-up version
    (single no-candidates early return). If that fix is ever reverted,
    these tests would still pass, since the dead code was provably
    unreachable and removing it didn't change behavior -- so this file
    cannot detect a regression-of-the-dead-code-coming-back. That's a
    real limitation, noted rather than silently glossed over.
  - SourceFactory.create_all()'s OWN internals (registry lookup, API
    key injection from config, RSS needing no key) are NOT covered in
    THIS file -- they belong in a dedicated test_source_factory.py,
    written separately. _get_next_event()'s tests here mock
    SourceFactory.create_all entirely; they prove _get_next_event()
    calls it and handles its return value correctly, not that the
    factory itself is correct.
"""
import pytest
from unittest.mock import MagicMock, patch, call

from app.orchestration import scheduler
from app.ingestion.base import BaseDataSource, RawArticle
from app.state import PipelineState


# ---------------------------------------------------------------------
# Shared fakes
# ---------------------------------------------------------------------

class _FakeSource(BaseDataSource):
    """A minimal real BaseDataSource subclass (not a MagicMock standing
    in for one) -- this means the inheritance/ABC contract from
    app/ingestion/base.py is genuinely exercised, not just assumed."""

    def __init__(self, articles=None, raise_on_fetch=False):
        self._articles = articles or []
        self._raise_on_fetch = raise_on_fetch

    def fetch_events(self) -> list[RawArticle]:
        if self._raise_on_fetch:
            raise RuntimeError("simulated source failure")
        return self._articles


def _make_article(title="Test article", content="Test content", source="test_source"):
    return RawArticle(source=source, title=title, content=content)


def _make_event(is_relevant=True):
    """Fake object standing in for app.agents.schemas.Event -- only the
    two attributes _get_next_event() actually touches (is_relevant,
    model_dump) need to exist."""
    fake = MagicMock()
    fake.is_relevant = is_relevant
    fake.model_dump.return_value = {"is_relevant": is_relevant, "event_type": "natural_disaster"}
    return fake


# ---------------------------------------------------------------------
# _get_next_event()
# ---------------------------------------------------------------------

class TestGetNextEvent:
    def test_returns_none_when_no_sources_return_anything(self):
        config = {}
        llm_client = MagicMock()

        with patch.object(scheduler.SourceFactory, "create_all", return_value=[_FakeSource(articles=[])]):
            result = scheduler._get_next_event(config, llm_client)

        assert result is None
        llm_client.generate.assert_not_called()

    def test_source_raising_is_skipped_not_fatal(self):
        # A failing source must not crash the whole cycle -- the other
        # source's articles should still be considered.
        good_article = _make_article(title="Flooding in Chennai")
        sources = [
            _FakeSource(raise_on_fetch=True),
            _FakeSource(articles=[good_article]),
        ]
        config = {}
        llm_client = MagicMock()
        llm_client.generate.return_value = _make_event(is_relevant=True)

        with patch.object(scheduler.SourceFactory, "create_all", return_value=sources):
            result = scheduler._get_next_event(config, llm_client)

        assert result is not None
        raw_article, structured_event = result
        assert raw_article["title"] == "Flooding in Chennai"

    def test_returns_first_relevant_article_in_fetch_order(self):
        irrelevant_article = _make_article(title="Irrelevant article")
        relevant_article = _make_article(title="Relevant article")
        config = {}
        llm_client = MagicMock()
        llm_client.generate.side_effect = [
            _make_event(is_relevant=False),
            _make_event(is_relevant=True),
        ]

        with patch.object(
            scheduler.SourceFactory,
            "create_all",
            return_value=[_FakeSource(articles=[irrelevant_article, relevant_article])],
        ):
            result = scheduler._get_next_event(config, llm_client)

        assert result is not None
        raw_article, _ = result
        assert raw_article["title"] == "Relevant article"
        assert llm_client.generate.call_count == 2

    def test_returns_none_when_no_candidate_is_relevant(self):
        articles = [_make_article(title=f"Article {i}") for i in range(3)]
        config = {}
        llm_client = MagicMock()
        llm_client.generate.return_value = _make_event(is_relevant=False)

        with patch.object(scheduler.SourceFactory, "create_all", return_value=[_FakeSource(articles=articles)]):
            result = scheduler._get_next_event(config, llm_client, max_candidates=5)

        assert result is None
        assert llm_client.generate.call_count == 3

    def test_max_candidates_caps_llm_calls(self):
        # 10 articles available, but max_candidates=3 -- only the first
        # 3 should ever reach the LLM, regardless of relevance.
        articles = [_make_article(title=f"Article {i}") for i in range(10)]
        config = {}
        llm_client = MagicMock()
        llm_client.generate.return_value = _make_event(is_relevant=False)

        with patch.object(scheduler.SourceFactory, "create_all", return_value=[_FakeSource(articles=articles)]):
            result = scheduler._get_next_event(config, llm_client, max_candidates=3)

        assert result is None
        assert llm_client.generate.call_count == 3

    def test_aggregates_candidates_across_multiple_sources(self):
        source_a = _FakeSource(articles=[_make_article(title="From source A")])
        source_b = _FakeSource(articles=[_make_article(title="From source B")])
        config = {}
        llm_client = MagicMock()
        # First candidate (source A's article) is irrelevant, second
        # (source B's) is relevant -- proves both sources' articles
        # actually got pooled into one candidate list, not just the
        # first source's.
        llm_client.generate.side_effect = [
            _make_event(is_relevant=False),
            _make_event(is_relevant=True),
        ]

        with patch.object(scheduler.SourceFactory, "create_all", return_value=[source_a, source_b]):
            result = scheduler._get_next_event(config, llm_client)

        assert result is not None
        raw_article, _ = result
        assert raw_article["title"] == "From source B"


# ---------------------------------------------------------------------
# run_pipeline_once()
# ---------------------------------------------------------------------

class TestRunPipelineOnce:
    def _patch_common(self, mock_get_next_event_return):
        """Returns a dict of patch context managers shared by most
        run_pipeline_once tests, to avoid repeating ~12 patch.object
        calls in every test. Caller is responsible for entering them
        via ExitStack or nested `with`."""
        return mock_get_next_event_return

    def test_no_event_found_returns_early_without_touching_db_writes(self):
        mock_db = MagicMock()
        with patch.object(scheduler, "SessionLocal", return_value=mock_db), \
             patch.object(scheduler, "load_config", return_value={"orchestration": {"confidence_threshold": 0.7, "micro_loop_max_iterations": 3}}), \
             patch.object(scheduler, "create_llm_client"), \
             patch.object(scheduler, "RAGClient"), \
             patch.object(scheduler, "EventExtractionAgent"), \
             patch.object(scheduler, "GeoAgent"), \
             patch.object(scheduler, "RiskAnalysisAgent"), \
             patch.object(scheduler, "SupplierAgent"), \
             patch.object(scheduler, "DecisionAgent"), \
             patch.object(scheduler, "SupervisorAgent"), \
             patch.object(scheduler, "build_graph"), \
             patch.object(scheduler, "_get_next_event", return_value=None), \
             patch.object(scheduler, "ApprovalQueueRepository"):

            scheduler.run_pipeline_once()

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.close.assert_called_once()

    def test_no_decision_proposal_returns_early_without_persisting(self):
        mock_db = MagicMock()
        mock_graph = MagicMock()
        # final_state ends up with decision_proposal=None (e.g.
        # is_relevant=False on the extracted event) -- nothing should
        # be persisted, but db.close() must still run.
        mock_graph.invoke.return_value = {"decision_proposal": None, "supervisor_feedback": None}

        with patch.object(scheduler, "SessionLocal", return_value=mock_db), \
             patch.object(scheduler, "load_config", return_value={"orchestration": {"confidence_threshold": 0.7, "micro_loop_max_iterations": 3}}), \
             patch.object(scheduler, "create_llm_client"), \
             patch.object(scheduler, "RAGClient"), \
             patch.object(scheduler, "EventExtractionAgent"), \
             patch.object(scheduler, "GeoAgent"), \
             patch.object(scheduler, "RiskAnalysisAgent"), \
             patch.object(scheduler, "SupplierAgent"), \
             patch.object(scheduler, "DecisionAgent"), \
             patch.object(scheduler, "SupervisorAgent"), \
             patch.object(scheduler, "build_graph", return_value=mock_graph), \
             patch.object(scheduler, "_get_next_event", return_value=({"title": "x", "content": "y", "source": "s"}, {})), \
             patch.object(scheduler, "ApprovalQueueRepository"):

            scheduler.run_pipeline_once()

        mock_db.add.assert_not_called()
        mock_db.commit.assert_not_called()
        mock_db.close.assert_called_once()

    def test_happy_path_persists_decision_and_approval_queue(self):
        mock_db = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "decision_proposal": {
                "action_type": "place_reorder",
                "target_supplier_name": "Mumbai Port Logistics Co",
                "target_product": "rice",
                "justification": "Flooding disrupts access",
                "magnitude": "moderate",
                "estimated_resolution_days": 7,
                "previously_rejected_options_checked": [],
            },
            "supervisor_feedback": {
                "confidence_score": 0.85,
                "approved": True,
                "critique": "Reasonable given the disruption",
                "suggested_revision": None,
                "proportionality_check": "proportional",
            },
            "hitl_framing": "high_confidence",
        }
        mock_approval_repo_cls = MagicMock()

        # db.refresh(decision) needs decision.id to exist afterwards for
        # the logger.info call and the ApprovalQueue construction --
        # simulate that the way a real DB would, by giving the object an
        # id attribute once "refreshed."
        def fake_refresh(obj):
            obj.id = 42
        mock_db.refresh.side_effect = fake_refresh

        with patch.object(scheduler, "SessionLocal", return_value=mock_db), \
             patch.object(scheduler, "load_config", return_value={"orchestration": {"confidence_threshold": 0.7, "micro_loop_max_iterations": 3}}), \
             patch.object(scheduler, "create_llm_client"), \
             patch.object(scheduler, "RAGClient"), \
             patch.object(scheduler, "EventExtractionAgent"), \
             patch.object(scheduler, "GeoAgent"), \
             patch.object(scheduler, "RiskAnalysisAgent"), \
             patch.object(scheduler, "SupplierAgent"), \
             patch.object(scheduler, "DecisionAgent"), \
             patch.object(scheduler, "SupervisorAgent"), \
             patch.object(scheduler, "build_graph", return_value=mock_graph), \
             patch.object(scheduler, "_get_next_event", return_value=({"title": "x", "content": "y", "source": "s"}, {})), \
             patch.object(scheduler, "ApprovalQueueRepository", mock_approval_repo_cls):

            scheduler.run_pipeline_once()

        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()
        persisted_decision = mock_db.add.call_args[0][0]
        assert persisted_decision.action_type == "place_reorder"
        assert persisted_decision.supervisor_approved is True  # confirms the approved -> supervisor_approved rename

        mock_approval_repo_cls.return_value.add.assert_called_once()
        persisted_queue_item = mock_approval_repo_cls.return_value.add.call_args[0][0]
        assert persisted_queue_item.decision_id == 42
        assert persisted_queue_item.hitl_framing == "high_confidence"
        assert persisted_queue_item.status == "unread"

        mock_db.close.assert_called_once()

    def test_missing_hitl_framing_defaults_to_low_confidence(self):
        # final_state.hitl_framing is None/falsy -> ApprovalQueue should
        # get "low_confidence", per `final_state.hitl_framing or
        # "low_confidence"` in the real code.
        mock_db = MagicMock()
        mock_graph = MagicMock()
        mock_graph.invoke.return_value = {
            "decision_proposal": {
                "action_type": "monitor_only",
                "target_supplier_name": "Some Supplier",
                "target_product": "wheat",
                "justification": "j",
                "magnitude": "low",
                "estimated_resolution_days": 1,
                "previously_rejected_options_checked": [],
            },
            "supervisor_feedback": {
                "confidence_score": 0.4,
                "approved": False,
                "critique": "c",
                "suggested_revision": "r",
                "proportionality_check": "proportional",
            },
            "hitl_framing": None,
        }
        mock_approval_repo_cls = MagicMock()
        mock_db.refresh.side_effect = lambda obj: setattr(obj, "id", 7)

        with patch.object(scheduler, "SessionLocal", return_value=mock_db), \
             patch.object(scheduler, "load_config", return_value={"orchestration": {"confidence_threshold": 0.7, "micro_loop_max_iterations": 3}}), \
             patch.object(scheduler, "create_llm_client"), \
             patch.object(scheduler, "RAGClient"), \
             patch.object(scheduler, "EventExtractionAgent"), \
             patch.object(scheduler, "GeoAgent"), \
             patch.object(scheduler, "RiskAnalysisAgent"), \
             patch.object(scheduler, "SupplierAgent"), \
             patch.object(scheduler, "DecisionAgent"), \
             patch.object(scheduler, "SupervisorAgent"), \
             patch.object(scheduler, "build_graph", return_value=mock_graph), \
             patch.object(scheduler, "_get_next_event", return_value=({"title": "x", "content": "y", "source": "s"}, {})), \
             patch.object(scheduler, "ApprovalQueueRepository", mock_approval_repo_cls):

            scheduler.run_pipeline_once()

        persisted_queue_item = mock_approval_repo_cls.return_value.add.call_args[0][0]
        assert persisted_queue_item.hitl_framing == "low_confidence"

    def test_exception_during_run_is_reraised_after_db_close(self):
        # The try/except/finally in run_pipeline_once logs and re-raises
        # on any exception, but db.close() must still happen via finally
        # -- a real DB session leak on every pipeline error would be a
        # serious, separate problem.
        mock_db = MagicMock()

        with patch.object(scheduler, "SessionLocal", return_value=mock_db), \
             patch.object(scheduler, "load_config", side_effect=RuntimeError("config load failed")):

            with pytest.raises(RuntimeError, match="config load failed"):
                scheduler.run_pipeline_once()

        mock_db.close.assert_called_once()

    def test_pipelinestate_silently_ignores_unexpected_extra_keys(self):
        # CONFIRMED behavior, not assumed: PipelineState has no
        # extra="forbid" config, so Pydantic v2's default "ignore"
        # behavior applies. This is a real characteristic of the
        # PipelineState(**result) call in run_pipeline_once -- a typo'd
        # or renamed key in graph.invoke()'s return would silently
        # vanish rather than raise. This test documents that behavior
        # directly against the real PipelineState class, not against
        # scheduler.py's usage of it.
        state = PipelineState(decision_proposal={"a": 1}, some_key_that_does_not_exist="should be ignored")
        assert state.decision_proposal == {"a": 1}
        assert not hasattr(state, "some_key_that_does_not_exist")


# ---------------------------------------------------------------------
# start_scheduler()
# ---------------------------------------------------------------------

class TestStartScheduler:
    def test_registers_interval_job_with_configured_hours(self):
        mock_scheduler_instance = MagicMock()
        config = {"orchestration": {"macro_loop_interval_hours": 6}}

        with patch.object(scheduler, "load_config", return_value=config), \
             patch.object(scheduler, "BackgroundScheduler", return_value=mock_scheduler_instance), \
             patch.object(scheduler, "run_pipeline_once") as mock_run_once:

            scheduler.start_scheduler()

        mock_scheduler_instance.add_job.assert_called_once()
        _, kwargs = mock_scheduler_instance.add_job.call_args
        assert kwargs["trigger"] == "interval"
        assert kwargs["hours"] == 6
        assert kwargs["id"] == "macro_loop"
        assert kwargs["next_run_time"] is None

    def test_starts_scheduler_and_runs_once_immediately(self):
        mock_scheduler_instance = MagicMock()
        config = {"orchestration": {"macro_loop_interval_hours": 6}}

        with patch.object(scheduler, "load_config", return_value=config), \
             patch.object(scheduler, "BackgroundScheduler", return_value=mock_scheduler_instance), \
             patch.object(scheduler, "run_pipeline_once") as mock_run_once:

            scheduler.start_scheduler()

        mock_scheduler_instance.start.assert_called_once()
        mock_run_once.assert_called_once()

    def test_returns_the_scheduler_instance(self):
        mock_scheduler_instance = MagicMock()
        config = {"orchestration": {"macro_loop_interval_hours": 6}}

        with patch.object(scheduler, "load_config", return_value=config), \
             patch.object(scheduler, "BackgroundScheduler", return_value=mock_scheduler_instance), \
             patch.object(scheduler, "run_pipeline_once"):

            result = scheduler.start_scheduler()

        assert result is mock_scheduler_instance

    def test_job_scheduled_before_immediate_run_not_after(self):
        # Order matters: add_job (scheduling future runs) should happen
        # before the manual immediate run, matching the real function's
        # written order. Using a shared call-order list rather than
        # asserting timestamps.
        mock_scheduler_instance = MagicMock()
        call_order = []
        mock_scheduler_instance.add_job.side_effect = lambda *a, **kw: call_order.append("add_job")
        config = {"orchestration": {"macro_loop_interval_hours": 6}}

        with patch.object(scheduler, "load_config", return_value=config), \
             patch.object(scheduler, "BackgroundScheduler", return_value=mock_scheduler_instance), \
             patch.object(scheduler, "run_pipeline_once", side_effect=lambda: call_order.append("run_pipeline_once")):

            scheduler.start_scheduler()

        assert call_order == ["add_job", "run_pipeline_once"]