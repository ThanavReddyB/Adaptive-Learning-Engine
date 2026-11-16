from models.state import LearningState
from utils.config import MAX_ATTEMPTS

# Routing labels must match the keys in add_conditional_edges
ADVANCE = "advance"
FOLLOWUP = "followup"
SIMPLIFY = "simplify"


def route_from_router_node(state: LearningState) -> str:
    """
    Determine the next branch after router_node has updated next_action.

    Returns one of: "advance" | "followup" | "simplify"
    """
    next_action = state.get("next_action", FOLLOWUP)

    if next_action == ADVANCE:
        return ADVANCE
    if next_action == SIMPLIFY:
        return SIMPLIFY
    return FOLLOWUP
