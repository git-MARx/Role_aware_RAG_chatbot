from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from backend.graph.state import GraphState, SubQueryState
from backend.graph.nodes.load_pending_action import load_pending_action_node
from backend.graph.nodes.query_rewriter import query_rewriter_node
from backend.graph.nodes.decomposer import decomposer_node
from backend.graph.nodes.classifier import classifier_node
from backend.graph.nodes.retrieval_node import retrieval_node
from backend.graph.nodes.grader import grader_node
from backend.graph.nodes.generator import generator_node
from backend.graph.nodes.action_node import action_node
from backend.tools.sql_tool import sql_tool_node


def _subgraph_send(state: GraphState, sub_query: str, pending: dict | None = None) -> dict:
    return {
        "emp_id":             state["emp_id"],
        "role":               state["role"],
        "manager_id":         state["manager_id"],
        "thread_id":          state["thread_id"],
        "original_sub_query": sub_query,
        "category":           "",
        "data_type":          None,
        "target_name":        None,
        "action_type":        None,
        "action_params":      {},
        "pending_action":     pending,
        "retrieved_chunks":   None,
        "sub_results":        [],
    }


def route_after_load(state: GraphState):
    pending = state.get("pending_action")
    if pending:
        return [Send("subgraph", _subgraph_send(state, state["original_query"], pending))]
    return "query_rewriter"


def route_after_rewriter(_state: GraphState):
    return "decomposer"


def route_after_decomposer(state: GraphState):
    return [
        Send("subgraph", _subgraph_send(state, sub_query))
        for sub_query in state["sub_queries"]
    ]


def route_subgraph_start(state: SubQueryState) -> str:
    if state.get("pending_action"):
        return "action_node"
    return "classifier"


def route_after_classifier(state: SubQueryState) -> str:
    category = state["category"]
    if category == "chitchat":
        return "chitchat"
    if category == "policy":
        return "retrieval"
    if category == "other":
        return "other"
    if category == "action":
        return "action_node"
    return "sql_tool"


def handle_other(state: SubQueryState) -> dict:
    return {"sub_results": [{
        "query": state["original_sub_query"],
        "type":  "other",
        "data":  "This is not an HR-related query.",
    }]}


subgraph = StateGraph(SubQueryState)

subgraph.add_node("classifier",  classifier_node)
subgraph.add_node("other",       handle_other)
subgraph.add_node("retrieval",   retrieval_node)
subgraph.add_node("grader",      grader_node)
subgraph.add_node("sql_tool",    sql_tool_node)
subgraph.add_node("action_node", action_node)

subgraph.add_conditional_edges(START, route_subgraph_start, {
    "classifier":  "classifier",
    "action_node": "action_node",
})
subgraph.add_conditional_edges("classifier", route_after_classifier, {
    "chitchat":   END,
    "other":      "other",
    "retrieval":  "retrieval",
    "sql_tool":   "sql_tool",
    "action_node": "action_node",
})
subgraph.add_edge("retrieval", "grader")
subgraph.set_finish_point("grader")
subgraph.set_finish_point("sql_tool")
subgraph.set_finish_point("other")
subgraph.set_finish_point("action_node")
subgraph = subgraph.compile()

builder = StateGraph(GraphState)

builder.add_node("load_pending_action", load_pending_action_node)
builder.add_node("query_rewriter",      query_rewriter_node)
builder.add_node("decomposer",          decomposer_node)
builder.add_node("subgraph",            subgraph)
builder.add_node("generator",           generator_node)

builder.add_edge(START,                  "load_pending_action")
builder.add_conditional_edges("load_pending_action", route_after_load, ["query_rewriter", "subgraph"])
builder.add_conditional_edges("query_rewriter", route_after_rewriter, ["decomposer"])
builder.add_conditional_edges("decomposer", route_after_decomposer, ["subgraph"])
builder.add_edge("subgraph",             "generator")
builder.add_edge("generator",            END)

graph = builder.compile()

from pathlib import Path
_base = Path(__file__).parent.parent.parent

with open(_base / "subgraph.png", "wb") as f:
    f.write(subgraph.get_graph().draw_png())

with open(_base / "graph.png", "wb") as f:
    f.write(graph.get_graph().draw_png())

if __name__ == "__main__":
    from config.settings import redis_client

    TEST_THREAD = "test-graph-thread"
    redis_client.delete(f"history:{TEST_THREAD}")

    def make_state(query: str) -> GraphState:
        return {
            "emp_id": 5, "role": "employee", "manager_id": 2,
            "department": "Engineering", "thread_id": TEST_THREAD,
            "original_query": query, "rewritten_query": "",
            "query_type": "", "sub_queries": [],
            "sub_results": [], "pending_action": None, "final_response": None,
        }

    test_cases = [
        # ("Chitchat", "Hello, how are you?"),
        # ("Policy",   "What is the maternity leave policy?"),
        # ("Personal", "What is my total leave balance?"),
        ("Multi",    "What is my total leave balance and what is the maternity leave policy?"),
    ]

    for label, query in test_cases:
        print(f"\n{'='*60}")
        print(f"Test: {label} — {query}")
        print("=" * 60)
        result = graph.invoke(make_state(query))
        print(f"Query type : {result['query_type']}")
        print(f"Sub queries: {result['sub_queries']}")
        print(f"Response   : {result['final_response']}")

    redis_client.delete(f"history:{TEST_THREAD}")
