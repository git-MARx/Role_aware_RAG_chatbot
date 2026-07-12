from backend.graph.state import GraphState
from backend.memory.redis_history import get_pending_action


def load_pending_action_node(state: GraphState) -> dict:
    return {"pending_action": get_pending_action(state["thread_id"])}
