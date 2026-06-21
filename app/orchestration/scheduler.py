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
from app.ingestion.factory import SourceFactory
from app.agents.event_extraction import EXTRACTION_PROMPT_TEMPLATE

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


def _get_next_event(config: dict, llm_client, max_candidates: int = 5) -> tuple[dict, dict] | None:
    """Fetches from all active ingestion sources, then runs candidates
    through Event Extraction Agent (in fetch order, across all sources)
    until one comes back is_relevant=True, or max_candidates is reached.

    Returns (raw_article_dict, structured_event_dict) for the first
    relevant article found. The structured_event is currently discarded
    by the caller (run_pipeline_once() re-runs Event Extraction inside
    the graph) -- returning it here anyway keeps this function's
    contract self-documenting and leaves the door open to wire it
    through later without changing this signature again.

    Returns None if no relevant article is found within max_candidates
    tries, or if no sources returned anything at all.

    max_candidates bounds LLM spend per cycle -- each candidate costs
    one Event Extraction call regardless of relevance, so this is a
    real, deliberate cap given free-tier quota constraints, not an
    arbitrary number. Tune via config if it needs adjusting later.
    """
    from app.agents.schemas import Event  # local import avoids a cycle with agents importing scheduler indirectly

    sources = SourceFactory.create_all(config)
    candidates: list[dict] = []

    for source in sources:
        try:
            articles = source.fetch_events()
        except Exception:
            logger.exception(
                "Macro loop: ingestion source %s failed, skipping",
                type(source).__name__,
            )
            continue
        candidates.extend(a.model_dump(mode="json") for a in articles)

    if not candidates:
        logger.warning("Macro loop: no articles found from any active source this cycle")
        return None

    logger.info(
        "Macro loop: %d candidate article(s) found, checking relevance "
        "(up to %d candidates)", len(candidates), max_candidates,
    )

    for raw_article in candidates[:max_candidates]:
        prompt = EXTRACTION_PROMPT_TEMPLATE.format(
            title=raw_article["title"], content=raw_article["content"],
        )
        event: Event = llm_client.generate(prompt, Event)
        if event.is_relevant:
            logger.info(
                "Macro loop: found relevant article: %r", raw_article["title"],
            )
            return raw_article, event.model_dump(mode="json")
        logger.info(
            "Macro loop: skipping irrelevant article: %r", raw_article["title"],
        )

    logger.warning(
        "Macro loop: no relevant article found among %d candidates this cycle",
        min(len(candidates), max_candidates),
    )
    return None
    

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

        result = _get_next_event(config, llm_client)
        if result is None:
            logger.info("Macro loop: nothing relevant to process this cycle, skipping")
            return

        raw_article, _extracted_event = result

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