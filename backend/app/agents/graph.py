"""The Praxis agent graph (LangGraph).

    resolver -> router ─┬─ (standard) ─> retriever -> synthesizer -> verifier -> (end)
                        │                                  ^                        |
                        │                                  └──── reviser ←── (ungrounded, once)
                        └─ (contradiction) ─> conflict_detector ──────────────────> (end)

The orchestrator is the graph plus its conditional edges: the router fans out by
intent (conflict questions take the dedicated detector), and the verifier only
releases a standard answer once it passes the grounding check (or after one
bounded revision).
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from .nodes import (
    after_verify,
    detect_conflicts,
    prepare_revision,
    resolve_references,
    retrieve,
    route,
    route_intent,
    synthesize,
    verify,
)
from .state import AgentState

_graph = None


def build_graph():
    g = StateGraph(AgentState)
    g.add_node("resolver", resolve_references)
    g.add_node("router", route)
    g.add_node("retriever", retrieve)
    g.add_node("conflict_detector", detect_conflicts)
    g.add_node("synthesizer", synthesize)
    g.add_node("verifier", verify)
    g.add_node("reviser", prepare_revision)

    g.set_entry_point("resolver")
    g.add_edge("resolver", "router")
    # router fans out by intent: contradiction questions take the conflict path.
    g.add_conditional_edges(
        "router", route_intent, {"conflict": "conflict_detector", "standard": "retriever"}
    )
    g.add_edge("conflict_detector", END)
    g.add_edge("retriever", "synthesizer")
    g.add_edge("synthesizer", "verifier")
    g.add_conditional_edges("verifier", after_verify, {"revise": "reviser", "end": END})
    g.add_edge("reviser", "synthesizer")
    return g.compile()


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
