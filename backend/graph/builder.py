"""
LangGraph graph construction.

Full flow:
  START
    → context_builder
    → explain_node
    → ask_node          ← INTERRUPT (graph pauses, waits for user_answer)
    → evaluate_node
    → misconception_node
    → feedback_node
    → router_node
        → advance  → END
        → followup → ask_node       (interrupt again)
        → simplify → explain_node   (re-explain → ask_node → interrupt again)
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from graph.nodes import (
    ask_node,
    context_builder,
    evaluate_node,
    explain_node,
    feedback_node,
    misconception_node,
    router_node,
)
from graph.router import ADVANCE, FOLLOWUP, SIMPLIFY, route_from_router_node
from models.state import LearningState

# ---------------------------------------------------------------------------
# Module-level singletons (one graph + one checkpointer for the process)
# ---------------------------------------------------------------------------

_checkpointer = MemorySaver()
_compiled_graph = None


def build_graph():
    """Build and compile the LangGraph StateGraph."""
    g = StateGraph(LearningState)

    # ── Register nodes ──────────────────────────────────────────────────
    g.add_node("context_builder", context_builder)
    g.add_node("explain_node", explain_node)
    g.add_node("ask_node", ask_node)
    g.add_node("evaluate_node", evaluate_node)
    g.add_node("misconception_node", misconception_node)
    g.add_node("feedback_node", feedback_node)
    g.add_node("router_node", router_node)

    # ── Entry point ──────────────────────────────────────────────────────
    g.set_entry_point("context_builder")

    # ── Linear edges ────────────────────────────────────────────────────
    g.add_edge("context_builder", "explain_node")
    g.add_edge("explain_node", "ask_node")
    # ask_node → evaluate_node is the post-interrupt continuation
    g.add_edge("ask_node", "evaluate_node")
    g.add_edge("evaluate_node", "misconception_node")
    g.add_edge("misconception_node", "feedback_node")
    g.add_edge("feedback_node", "router_node")

    # ── Conditional edges from router ────────────────────────────────────
    g.add_conditional_edges(
        "router_node",
        route_from_router_node,
        {
            ADVANCE: END,
            FOLLOWUP: "ask_node",    # same topic, new question
            SIMPLIFY: "explain_node",  # re-explain simpler → new question
        },
    )

    return g.compile(
        checkpointer=_checkpointer,
        interrupt_after=["ask_node"],  # pause after question is generated
    )


def get_graph():
    """Return the process-level compiled graph (lazy init)."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def get_thread_config(user_id: str) -> dict:
    """Return the LangGraph thread config dict for a given user."""
    return {"configurable": {"thread_id": user_id}}
