"""
First end-to-end test of the full RiskRadar pipeline.

Builds all six agents the "real" way (same construction logic
scheduler.py will eventually need: load_config() -> create_llm_client()
-> agent constructors), feeds one seeded article through
build_graph().invoke(), and prints the final state so each field can be
inspected manually.

This makes REAL Gemini API calls (5 of 6 nodes call the LLM) and a REAL
RAG query/embed pass. Expect this to take anywhere from ~10 seconds to
a couple of minutes depending on confidence/iteration count, and to use
real (free-tier) API quota.

Run from the repo root:
    python test_full_pipeline.py

If something fails, the traceback will point to which node/agent broke --
that's useful signal, not just noise. Read it before re-running.
"""
import json

from app.agents.decision import DecisionAgent
from app.agents.event_extraction import EventExtractionAgent
from app.agents.geo import GeoAgent
from app.agents.risk_analysis import RiskAnalysisAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.supplier import SupplierAgent
from app.db.session import SessionLocal
from app.llm.factory import create_llm_client
from app.orchestration.graph import build_graph
from app.rag.client import RAGClient
from app.state import PipelineState
from app.utils.config import load_config

# --- 1. load config + build shared clients (same as scheduler.py will need) ---
config = load_config()
llm_client = create_llm_client(config)
rag_client = RAGClient()
db = SessionLocal()

# --- 2. construct all six agents, matching each one's real __init__ signature ---
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

# --- 3. build the graph ---
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

# --- 4. one seeded test article (RawArticle shape: source, title, content required) ---
test_article = {
    "source": "manual_test",
    "title": "Major flooding disrupts highway access to Chennai port",
    "content": (
        "Heavy monsoon flooding has cut off road access to Chennai port "
        "for the third consecutive day, stranding container trucks on "
        "National Highway 45. Port authorities report significant delays "
        "in both inbound and outbound cargo. Local logistics firms "
        "estimate the disruption could last another week if rains "
        "continue as forecast. Several trucking companies have already "
        "begun rerouting shipments through alternate routes, adding "
        "2-3 days to delivery times."
    ),
}

initial_state = PipelineState(raw_article=test_article)

# --- 5. run it ---
print("Running full pipeline... (this calls the real Gemini API, may take a while)")
result = graph.invoke(initial_state)
final_state = PipelineState(**result)

# --- 6. report ---
print("\n" + "=" * 70)
print("PIPELINE RUN COMPLETE")
print("=" * 70)
print(f"iteration_count:   {final_state.iteration_count}")
print(f"confidence_score:  {final_state.confidence_score}")
print(f"hitl_framing:      {final_state.hitl_framing}")
print("-" * 70)
print("structured_event:")
print(json.dumps(final_state.structured_event, indent=2))
print("-" * 70)
print("affected_regions:")
print(json.dumps(final_state.affected_regions, indent=2))
print("-" * 70)
print("risk_assessment:")
print(json.dumps(final_state.risk_assessment, indent=2))
print("-" * 70)
print("supplier_impact:")
print(json.dumps(final_state.supplier_impact, indent=2))
print("-" * 70)
print("decision_proposal:")
print(json.dumps(final_state.decision_proposal, indent=2))
print("-" * 70)
print("supervisor_feedback:")
print(json.dumps(final_state.supervisor_feedback, indent=2))
print("=" * 70)

db.close()