"""
LangGraph StateGraph — wires all 6 agents as nodes, in pipeline order, with
the Decision <-> Supervisor micro loop implemented as a conditional edge
(based on confidence_score vs. config threshold, and iteration_count vs. max).

TODO (Day 2 evening — owner: poddar-aniket):
- Build this with 6 stub nodes (lambdas that just pass state through) first,
  so the graph topology is proven out before Day 3 — don't let it be a Day 3
  surprise on top of building the real agents.

TODO (Day 3 — owner: poddar-aniket):
- Swap stub nodes for real agent.run() calls as ash119821 finishes each agent.
- Add the conditional edge for the micro loop.
"""


def build_graph():
    raise NotImplementedError("Build LangGraph StateGraph — stub Day 2, real Day 3")
