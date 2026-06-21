"""
Macro loop scheduler — runs the full 6-agent LangGraph pipeline on a
recurring schedule (config: orchestration.macro_loop_interval_hours),
and once immediately on app startup.

For each run:
  1. Build a fresh DB session + all six agents (same construction pattern
     proven working in test_full_pipeline.py).
  2. Feed one event through build_graph().invoke().
  3. Persist the resulting Decision row.
  4. Persist a corresponding ApprovalQueue row (hitl_framing, status="unread").

CURRENT LIMITATION, DELIBERATE: events come from ONE_SEEDED_EVENT below,
not the real ingestion adapters (app/ingestion/newsdata.py, rss.py,
openweather.py). This isolates scheduler/persistence wiring from live
ingestion as a separate, later step -- swap _get_next_event()'s body
for a real SourceFactory call once this scheduler is confirmed working
end-to-end on its own.

Wire-up (in app/main.py, not yet done):
    from app.orchestration.scheduler import start_scheduler
    start_scheduler()
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler

from app.agents.decision import DecisionAgent
from app.agents.event_extraction import EventExtractionAgent
from app.agents.geo import GeoAgent
from app.agents.risk_analysis import RiskAnalysisAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.supplier import SupplierAgent
from app.db.approval_queue_repository import ApprovalQueueRepository
from app.db.session import SessionLocal
from app.llm.factory import create_llm_client
from app.models.approval_queue import ApprovalQueue
from app.models.decision import Decision
from app.orchestration.graph import build_graph
from app.rag.client import RAGClient
from app.state import PipelineState
from app.utils.config import load_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# TEMPORARY: one seeded event, standing in for real ingestion.
# See module docstring -- swap for SourceFactory/BaseDataSource once this
# scheduler is confirmed working end-to-end on its own.
# ---------------------------------------------------------------------------
ONE_SEEDED_EVENT = {
    "source": "manual_test",
    "title": "Major flooding disrupts highway access to Chennai port",
    "content": (
        "Heavy monsoon flooding has cut off road access to Chennai port "
        "for the third consecutive day, stranding container trucks on "
        "National Highway 45. Port authorities report significant delays "
        "in both inbound and outbound cargo. Local logistics firms "
        "estimate the disruption could last another week if rains "
        "continue as forecast."
    ),
}


def _get_next_event() -> dict:
    """Returns the next raw article to run through the pipeline.

    TEMPORARY: always returns the same seeded event. Replace with a real
    call through the ingestion adapters (SourceFactory.fetch_all() or
    similar) once the scheduler+persistence wiring is confirmed working.
    """
    return ONE_SEEDED_EVENT


def run_pipeline_once() -> None:
    """One full macro-loop cycle: build agents, run the graph on the next
    event, persist the resulting Decision + ApprovalQueue rows.

    Each call gets its own DB session, opened and closed within this
    function -- APScheduler jobs are not request-scoped the way FastAPI
    endpoints are, so there's no get_db() dependency to lean on here.
    """
    logger.info("Macro loop: starting pipeline run")
    db = SessionLocal()
    try:
        config = load_config()
        llm_client = create_llm_client(config)
        rag_client = RAGClient()

        event_extraction_agent = EventExtractionAgent(llm_client)
        geo_agent = GeoAgent(llm_client, rag_client)
        risk_analysis_agent = RiskAnalysisAgent(llm_client, db, rag_client)
        supplier_agent = SupplierAgent(llm_client, db)
        decision_agent = DecisionAgent(llm_client, rag_client)
        supervisor_agent = SupervisorAgent(
            llm_client,
            rag_client,
            confidence_threshold=config["orchestration"]["confidence_threshold"],
        )

        graph = build_graph(
            event_extraction_agent,
            geo_agent,
            risk_analysis_agent,
            supplier_agent,
            decision_agent,
            supervisor_agent,
            confidence_threshold=config["orchestration"]["confidence_threshold"],
            max_iterations=config["orchestration"]["micro_loop_max_iterations"],
        )

        raw_article = _get_next_event()
        initial_state = PipelineState(raw_article=raw_article)
        result = graph.invoke(initial_state)
        final_state = PipelineState(**result)

        if final_state.decision_proposal is None or final_state.supervisor_feedback is None:
            logger.warning(
                "Macro loop: pipeline finished with no decision_proposal/"
                "supervisor_feedback (likely is_relevant=False on the "
                "extracted event) -- nothing to persist this run."
            )
            return

        proposal = final_state.decision_proposal
        feedback = final_state.supervisor_feedback

        decision = Decision(
            action_type=proposal["action_type"],
            target_supplier_name=proposal["target_supplier_name"],
            target_product=proposal["target_product"],
            justification=proposal["justification"],
            magnitude=proposal["magnitude"],
            estimated_resolution_days=proposal["estimated_resolution_days"],
            previously_rejected_options_checked=proposal["previously_rejected_options_checked"],
            confidence_score=feedback["confidence_score"],
            # Note the deliberate rename: schema field is "approved",
            # model column is "supervisor_approved" -- see app/models/
            # decision.py's docstring for why these are kept distinct.
            supervisor_approved=feedback["approved"],
            critique=feedback["critique"],
            suggested_revision=feedback.get("suggested_revision"),
            proportionality_check=feedback["proportionality_check"],
            status="pending",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        logger.info("Macro loop: persisted Decision id=%d", decision.id)

        queue_item = ApprovalQueue(
            decision_id=decision.id,
            hitl_framing=final_state.hitl_framing or "low_confidence",
            status="unread",
        )
        ApprovalQueueRepository(db).add(queue_item)
        logger.info(
            "Macro loop: persisted ApprovalQueue id=%d for decision_id=%d (framing=%s)",
            queue_item.id, decision.id, queue_item.hitl_framing,
        )

    except Exception:
        logger.exception("Macro loop: pipeline run failed")
        raise
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    """Starts the macro loop: runs once immediately, then on the
    config-defined interval. Call once at app startup (app/main.py).

    Returns the scheduler instance so the caller can shut it down
    cleanly if needed (not currently wired into main.py's lifecycle --
    acceptable for a dev-mode --reload server, worth revisiting before
    any real deployment).
    """
    config = load_config()
    interval_hours = config["orchestration"]["macro_loop_interval_hours"]

    scheduler = BackgroundScheduler()
    scheduler.add_job(
        run_pipeline_once,
        trigger="interval",
        hours=interval_hours,
        id="macro_loop",
        next_run_time=None,  # we trigger the first run manually below, not via the trigger
    )
    scheduler.start()
    logger.info("Scheduler started: macro loop will run every %d hours", interval_hours)

    # Run once immediately on startup, in addition to the interval above --
    # useful for demos/testing so the queue isn't empty until the first
    # interval elapses.
    run_pipeline_once()

    return scheduler