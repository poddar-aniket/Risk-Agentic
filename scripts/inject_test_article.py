"""
Injects a fake relevant article directly into the pipeline, bypassing
NewsData/RSS/OpenWeather fetching and relevance checking.

Use this to test the full agent chain without burning Gemini quota.

Run from repo root:
    python -m scripts.inject_test_article
"""
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")

from app.agents.decision import DecisionAgent
from app.agents.event_extraction import EventExtractionAgent
from app.agents.geo import GeoAgent
from app.agents.risk_analysis import RiskAnalysisAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.supplier import SupplierAgent
from app.db.approval_queue_repository import ApprovalQueueRepository
from app.db.session import Base, SessionLocal, engine
from app.llm.factory import create_llm_client
from app.models import approval_queue, decision, event, inventory, supplier  # noqa
from app.models.approval_queue import ApprovalQueue
from app.models.decision import Decision
from app.orchestration.graph import build_graph
from app.rag.client import RAGClient
from app.state import PipelineState
from app.utils.config import load_config

Base.metadata.create_all(bind=engine)

# A realistic supply-chain disruption article that will definitely be
# marked is_relevant=True and map to seeded suppliers in Tamil Nadu /
# Maharashtra
FAKE_ARTICLE = {
    "source": "test_inject",
    "title": "Severe flooding shuts Chennai port, disrupts Maharashtra highway supply routes",
    "content": (
        "Heavy monsoon flooding has forced the complete shutdown of Chennai port "
        "for the fourth consecutive day, with over 200 vessels stranded offshore. "
        "Road connectivity via NH-44 linking Tamil Nadu to Maharashtra has been "
        "severely disrupted with multiple highway sections submerged under 3-4 feet "
        "of water. Major suppliers in Tamil Nadu including Chennai Textile Exports "
        "have reported complete inability to dispatch goods. Mumbai Port Logistics Co "
        "in Maharashtra is also reporting significant delays due to flooded approach "
        "roads. Industry bodies estimate the disruption will last at least 10-14 more "
        "days. Rice and wheat shipments are most severely affected, with cold storage "
        "facilities also reporting power outages. Kolkata Jute Mills has issued a "
        "force majeure notice citing inability to source raw materials."
    ),
    "url": "http://test.local/fake-article",
    "published_at": "2026-06-23",
}


def run():
    config = load_config()
    llm_client = create_llm_client(config)
    rag_client = RAGClient()
    db = SessionLocal()

    try:
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

        print("Running full pipeline on fake article...")
        initial_state = PipelineState(raw_article=FAKE_ARTICLE)
        result = graph.invoke(initial_state)
        final_state = PipelineState(**result)

        if final_state.decision_proposal is None or final_state.supervisor_feedback is None:
            print("Pipeline finished with no decision — article may have been marked not relevant.")
            return

        proposal = final_state.decision_proposal
        feedback = final_state.supervisor_feedback

        se_data = dict(final_state.structured_event) if final_state.structured_event else {}
        se_data["raw_article"] = FAKE_ARTICLE

        d = Decision(
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
        db.add(d)
        db.commit()
        db.refresh(d)
        print(f"Decision id={d.id} persisted")

        q = ApprovalQueue(
            decision_id=d.id,
            hitl_framing=final_state.hitl_framing or "low_confidence",
            status="unread",
        )
        ApprovalQueueRepository(db).add(q)

        print(f"\nDone! Check http://localhost:3000/queue")
        print(f"  Risk score:  {final_state.risk_assessment.get('risk_score')}")
        print(f"  Urgency:     {final_state.risk_assessment.get('urgency')}")
        print(f"  Action:      {proposal.get('action_type')}")
        print(f"  Target:      {proposal.get('target_supplier_name')} / {proposal.get('target_product')}")
        print(f"  Confidence:  {final_state.confidence_score}")
        print(f"  Framing:     {final_state.hitl_framing}")
        print(f"  Iterations:  {final_state.iteration_count}")

    finally:
        db.close()


if __name__ == "__main__":
    run()