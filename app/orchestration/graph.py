"""
LangGraph StateGraph — wires all 6 agents as nodes in pipeline order, with
the Decision <-> Supervisor micro loop as a conditional edge.

PIPELINE ORDER:
  event_extraction → geo → risk_analysis → supplier → decision → supervisor
                                                           ↑           |
                                                           └───────────┘
                                              (conditional: loop if confidence
                                               < threshold AND iterations < max)

MICRO LOOP LOGIC (conditional edge after supervisor node):
  - confidence >= threshold                → EXIT loop → hitl_framing
  - confidence < threshold AND iter < max  → BACK to decision node (revision)
  - iterations exhausted                   → EXIT loop → hitl_framing (low confidence)

HOW TO USE:
  from app.orchestration.graph import build_graph
  from app.state import PipelineState

  graph = build_graph(agents, config)
  final_state = graph.invoke(PipelineState(raw_article=article.model_dump()))
"""
import logging
from typing import Literal

from langgraph.graph import END, StateGraph

from app.agents.decision import DecisionAgent
from app.agents.event_extraction import EventExtractionAgent
from app.agents.geo import GeoAgent
from app.agents.risk_analysis import RiskAnalysisAgent
from app.agents.supervisor import SupervisorAgent
from app.agents.supplier import SupplierAgent
from app.state import PipelineState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Node functions — thin wrappers that call agent.run() and return the state
# as a dict (LangGraph requires nodes to return dict, not Pydantic model)
# ---------------------------------------------------------------------------

def make_event_extraction_node(agent: EventExtractionAgent):
    def node(state: PipelineState) -> dict:
        logger.info("Node: event_extraction")
        return agent.run(state).model_dump()
    return node


def make_geo_node(agent: GeoAgent):
    def node(state: PipelineState) -> dict:
        logger.info("Node: geo")
        return agent.run(state).model_dump()
    return node


def make_risk_analysis_node(agent: RiskAnalysisAgent):
    def node(state: PipelineState) -> dict:
        logger.info("Node: risk_analysis")
        return agent.run(state).model_dump()
    return node


def make_supplier_node(agent: SupplierAgent):
    def node(state: PipelineState) -> dict:
        logger.info("Node: supplier")
        return agent.run(state).model_dump()
    return node


def make_decision_node(agent: DecisionAgent):
    def node(state: PipelineState) -> dict:
        logger.info("Node: decision (iteration %d)", state.iteration_count)
        return agent.run(state).model_dump()
    return node


def make_supervisor_node(agent: SupervisorAgent):
    def node(state: PipelineState) -> dict:
        logger.info("Node: supervisor")
        return agent.run(state).model_dump()
    return node


# ---------------------------------------------------------------------------
# HITL framing node — runs after the micro loop exits, sets hitl_framing
# on the state so the FastAPI queue endpoint can frame the item correctly
# ---------------------------------------------------------------------------

def hitl_framing_node(state: PipelineState) -> dict:
    """Sets hitl_framing based on final confidence score."""
    threshold = 7.0  # matches config.yaml orchestration.confidence_threshold
    score = state.confidence_score or 0.0
    framing = "high_confidence" if score >= threshold else "low_confidence"
    logger.info(
        "HITL framing: %s (confidence=%.1f, iterations=%d)",
        framing, score, state.iteration_count,
    )
    return {"hitl_framing": framing}


# ---------------------------------------------------------------------------
# Conditional edge — decides whether to loop back to Decision or exit
# ---------------------------------------------------------------------------

def micro_loop_router(
    state: PipelineState,
    confidence_threshold: float = 7.0,
    max_iterations: int = 5,
) -> Literal["decision", "hitl_framing"]:
    """
    Called after each Supervisor run.
    Returns "decision" to loop back, "hitl_framing" to exit.
    """
    score = state.confidence_score or 0.0
    iterations = state.iteration_count

    if score >= confidence_threshold:
        logger.info("Micro loop EXIT — confidence %.1f >= threshold %.1f", score, confidence_threshold)
        return "hitl_framing"

    if iterations >= max_iterations:
        logger.warning(
            "Micro loop EXIT — max iterations (%d) exhausted, confidence %.1f below threshold",
            max_iterations, score,
        )
        return "hitl_framing"

    logger.info(
        "Micro loop CONTINUE — confidence %.1f < threshold %.1f, iteration %d/%d",
        score, confidence_threshold, iterations, max_iterations,
    )
    return "decision"


# ---------------------------------------------------------------------------
# Graph builder — call this once at app startup with injected agents
# ---------------------------------------------------------------------------

def build_graph(
    event_extraction_agent: EventExtractionAgent,
    geo_agent: GeoAgent,
    risk_analysis_agent: RiskAnalysisAgent,
    supplier_agent: SupplierAgent,
    decision_agent: DecisionAgent,
    supervisor_agent: SupervisorAgent,
    confidence_threshold: float = 7.0,
    max_iterations: int = 5,
):
    """
    Builds and compiles the LangGraph StateGraph.

    All agents are injected here (not instantiated inside this function)
    so dependency injection stays clean and the graph is testable with
    fake agents.

    Usage:
        graph = build_graph(agent1, agent2, ..., confidence_threshold=7.0)
        result = graph.invoke(initial_state.model_dump())
        final_state = PipelineState(**result)
    """
    graph = StateGraph(PipelineState)

    # --- register nodes ---
    graph.add_node("event_extraction", make_event_extraction_node(event_extraction_agent))
    graph.add_node("geo", make_geo_node(geo_agent))
    graph.add_node("risk_analysis", make_risk_analysis_node(risk_analysis_agent))
    graph.add_node("supplier", make_supplier_node(supplier_agent))
    graph.add_node("decision", make_decision_node(decision_agent))
    graph.add_node("supervisor", make_supervisor_node(supervisor_agent))
    graph.add_node("hitl_framing", hitl_framing_node)

    # --- linear edges (pipeline order) ---
    graph.set_entry_point("event_extraction")
    graph.add_edge("event_extraction", "geo")
    graph.add_edge("geo", "risk_analysis")
    graph.add_edge("risk_analysis", "supplier")
    graph.add_edge("supplier", "decision")
    graph.add_edge("decision", "supervisor")

    # --- conditional edge: micro loop ---
    graph.add_conditional_edges(
        "supervisor",
        lambda state: micro_loop_router(state, confidence_threshold, max_iterations),
        {
            "decision": "decision",       # loop back
            "hitl_framing": "hitl_framing",  # exit
        },
    )

    graph.add_edge("hitl_framing", END)

    return graph.compile()
