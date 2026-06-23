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

def _get_next_event(config: dict, llm_client, db, rag_client, max_candidates: int = 3) -> tuple[dict, dict] | None:
    """Fetches from all active ingestion sources, then runs candidates
    through Event Extraction Agent (in fetch order, across all sources)
    until one comes back is_relevant=True, or max_candidates is reached.

    Filters out candidate articles that have already been processed by checking
    against stored raw_article metadata in existing decisions, as well as checking
    semantic similarity in RAG's past_events collection.
    """
    from app.agents.schemas import Event  # local import avoids a cycle with agents importing scheduler indirectly

    # Query existing decision raw article titles and urls to check for exact duplicates
    processed_titles = set()
    processed_urls = set()
    try:
        from app.models.decision import Decision
        existing_decisions = db.query(Decision).all()
        for d in existing_decisions:
            if d.structured_event:
                raw_art = d.structured_event.get("raw_article")
                if raw_art:
                    t = raw_art.get("title")
                    u = raw_art.get("url")
                    if t:
                        processed_titles.add(t.strip().lower())
                    if u:
                        processed_urls.add(u.strip().lower())
    except Exception as e:
        logger.warning("Could not fetch existing decisions for duplicate checking: %s", e)

    import os
    use_mock = os.getenv("USE_MOCK_INGESTION", "false").lower() == "true"
    candidates: list[dict] = []

    if use_mock:
        logger.info("Macro loop: using mock ingestion source as configured.")
        candidates = [
            {
                "source": "mock_news",
                "title": "6.4 Magnitude Earthquake Strikes Hsinchu Science Park, Halting Chip Production",
                "content": (
                    "A strong 6.4 magnitude earthquake struck Taiwan's Hsinchu region early Tuesday morning, "
                    "prompting precautionary evacuations and temporary power shutdowns at key semiconductor manufacturing "
                    "facilities. Officials report minor structural damages to cleanrooms, and production lines have been "
                    "halted for safety checks. Shipping delays of critical microcontrollers and logic chips are expected "
                    "to impact global electronics suppliers for the next two weeks."
                ),
                "url": "https://mocknews.io/taiwan-earthquake-semiconductors",
                "published_at": "2026-06-23T08:00:00Z"
            },
            {
                "source": "mock_news",
                "title": "Rotterdam Port Operations Grind to a Halt as Workers Begin Indefinite Strike",
                "content": (
                    "Port operations at the Port of Rotterdam, Europe's largest shipping hub, have come to a standstill "
                    "following a breakdown in wage negotiations between harbor unions and terminal operators. The labor "
                    "strike has closed three major container terminals, causing shipping lines to reroute cargo ships to "
                    "secondary ports. Logistics analysts warn of significant inbound delays of raw materials, chemical compounds, "
                    "and machinery parts."
                ),
                "url": "https://mocknews.io/rotterdam-port-workers-strike",
                "published_at": "2026-06-23T09:00:00Z"
            },
            {
                "source": "mock_news",
                "title": "Chennai Industrial Hub cut off by Severe Monsoon Floods",
                "content": (
                    "Torrential monsoon rains have triggered severe flooding in Chennai's Oragadam industrial corridor, "
                    "cutting off major highway routes leading to the Chennai Port. Warehouses and automotive assembly plants "
                    "have suspended operations due to waterlogging and localized power outages. Fleet management firms report "
                    "hundreds of container trucks stranded on national highways, disrupting delivery windows of finished assemblies."
                ),
                "url": "https://mocknews.io/chennai-monsoon-floods-logistics",
                "published_at": "2026-06-23T10:00:00Z"
            }
        ]
    else:
        sources = SourceFactory.create_all(config)
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

    # Filter out duplicates (both exact and semantic RAG checks)
    unique_candidates = []
    for c in candidates:
        title = c.get("title", "").strip().lower()
        url = c.get("url", "").strip().lower() if c.get("url") else ""
        
        # 1. Exact match checks
        if title in processed_titles or (url and url in processed_urls):
            logger.info("Macro loop: skipping exact duplicate candidate article: %r", c.get("title"))
            continue

        # 2. Semantic RAG check for similar articles
        try:
            results = rag_client.query("past_events", c.get("title", ""), top_k=1)
            if results:
                match = results[0]
                distance = match.get("distance", 1.0)
                # Cosine distance < 0.20 represents high semantic similarity (e.g. same event reported by another outlet)
                if distance < 0.20:
                    logger.info(
                        "Macro loop: skipping semantically similar article in history (distance=%f): %r",
                        distance, c.get("title")
                    )
                    continue
        except Exception as re:
            logger.warning("RAG similarity duplicate check failed: %s", re)
            
        unique_candidates.append(c)

    if not unique_candidates:
        logger.warning("Macro loop: all fetched articles have already been processed.")
        return None

    logger.info(
        "Macro loop: %d candidate article(s) found, checking relevance "
        "(up to %d candidates)", len(unique_candidates), max_candidates,
    )

    for raw_article in unique_candidates[:max_candidates]:
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
        min(len(unique_candidates), max_candidates),
    )
    return None
    

def run_pipeline_once() -> str:
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

        result = _get_next_event(config, llm_client, db, rag_client)
        if result is None:
            logger.info("Macro loop: nothing relevant to process this cycle, skipping")
            return "skipped"

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
            return "skipped"

        proposal = final_state.decision_proposal
        feedback = final_state.supervisor_feedback

        # Save raw_article inside structured_event metadata for future duplicate check
        se_data = dict(final_state.structured_event) if final_state.structured_event else {}
        se_data["raw_article"] = raw_article

        decision = Decision(
            action_type=proposal["action_type"],
            target_supplier_name=proposal["target_supplier_name"],
            target_product=proposal["target_product"],
            justification=proposal["justification"],
            magnitude=proposal["magnitude"],
            estimated_resolution_days=proposal["estimated_resolution_days"],
            previously_rejected_options_checked=proposal["previously_rejected_options_checked"],
            confidence_score=feedback["confidence_score"],
            supervisor_approved=feedback["approved"],
            critique=feedback["critique"],
            suggested_revision=feedback.get("suggested_revision"),
            proportionality_check=feedback["proportionality_check"],
            status="pending",
            structured_event=se_data,
            affected_regions=final_state.affected_regions,
            risk_assessment=final_state.risk_assessment,
            supplier_impact=final_state.supplier_impact,
            decision_proposal=final_state.decision_proposal,
            supervisor_feedback=final_state.supervisor_feedback,
            iteration_count=final_state.iteration_count,
            hitl_framing=final_state.hitl_framing or "low_confidence",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        logger.info("Macro loop: persisted Decision id=%d", decision.id)

        # Store in RAG past_events collection to block similar duplicates semantically in future runs
        try:
            document_text = f"{raw_article['title']}. {raw_article['content']}"
            rag_client.add(
                "past_events",
                documents=[document_text],
                metadatas=[{
                    "title": raw_article["title"],
                    "url": raw_article.get("url") or "",
                    "is_relevant": 1
                }],
                ids=[f"decision_event_{decision.id}"]
            )
            logger.info("Macro loop: indexed successfully processed event into RAG past_events")
        except Exception as e:
            logger.warning("Failed to store decision in RAG: %s", e)

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
        return "success"


    except Exception:
        logger.exception("Macro loop: pipeline run failed")
        raise
    finally:
        db.close()
def stream_pipeline():
    """Generates streaming pipeline execution status events, suitable for SSE."""
    logger.info("Macro loop: starting streaming pipeline run")
    db = SessionLocal()
    try:
        config = load_config()
        llm_client = create_llm_client(config)
        rag_client = RAGClient()

        yield {"status": "ingesting", "message": "Fetching news and weather data feeds..."}

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

        result = _get_next_event(config, llm_client, db, rag_client)
        if result is None:
            logger.info("Macro loop: nothing relevant to process this cycle, skipping")
            yield {"status": "skipped", "message": "No new relevant articles found in this ingestion cycle."}
            return

        raw_article, _extracted_event = result
        yield {"status": "start", "message": f"Article found: \"{raw_article.get('title')[:60]}...\"", "raw_article": raw_article}

        initial_state = PipelineState(raw_article=raw_article)
        
        state_accum = dict(initial_state.model_dump())
        for event in graph.stream(initial_state):
            node_name = list(event.keys())[0]
            node_output = event[node_name]
            state_accum.update(node_output)
            yield {"status": "progress", "node": node_name, "message": f"Agent node [{node_name}] finished execution."}

        final_state = PipelineState(**state_accum)

        if final_state.decision_proposal is None or final_state.supervisor_feedback is None:
            logger.warning("Macro loop: pipeline finished with no decision/feedback.")
            yield {"status": "skipped", "message": "Article analyzed but did not warrant supply chain action proposal."}
            return

        proposal = final_state.decision_proposal
        feedback = final_state.supervisor_feedback

        se_data = dict(final_state.structured_event) if final_state.structured_event else {}
        se_data["raw_article"] = raw_article

        decision = Decision(
            action_type=proposal["action_type"],
            target_supplier_name=proposal["target_supplier_name"],
            target_product=proposal["target_product"],
            justification=proposal["justification"],
            magnitude=proposal["magnitude"],
            estimated_resolution_days=proposal["estimated_resolution_days"],
            previously_rejected_options_checked=proposal["previously_rejected_options_checked"],
            confidence_score=feedback["confidence_score"],
            supervisor_approved=feedback["approved"],
            critique=feedback["critique"],
            suggested_revision=feedback.get("suggested_revision"),
            proportionality_check=feedback["proportionality_check"],
            status="pending",
            structured_event=se_data,
            affected_regions=final_state.affected_regions,
            risk_assessment=final_state.risk_assessment,
            supplier_impact=final_state.supplier_impact,
            decision_proposal=final_state.decision_proposal,
            supervisor_feedback=final_state.supervisor_feedback,
            iteration_count=final_state.iteration_count,
            hitl_framing=final_state.hitl_framing or "low_confidence",
        )
        db.add(decision)
        db.commit()
        db.refresh(decision)
        logger.info("Macro loop: persisted Decision id=%d", decision.id)

        # Store in RAG past_events collection to block similar duplicates semantically in future runs
        try:
            document_text = f"{raw_article['title']}. {raw_article['content']}"
            rag_client.add(
                "past_events",
                documents=[document_text],
                metadatas=[{
                    "title": raw_article["title"],
                    "url": raw_article.get("url") or "",
                    "is_relevant": 1
                }],
                ids=[f"decision_event_{decision.id}"]
            )
            logger.info("Macro loop: indexed successfully processed event into RAG past_events")
        except Exception as e:
            logger.warning("Failed to store decision in RAG: %s", e)

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
        yield {"status": "completed", "message": "Pipeline executed successfully. New decision entry logged.", "decision_id": decision.id}

    except Exception as e:
        logger.exception("Macro loop: pipeline run failed")
        yield {"status": "error", "message": f"Pipeline run failed: {str(e)}"}
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