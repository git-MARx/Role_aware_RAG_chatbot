from langgraph.graph import StateGraph, START, END
from langgraph.types import Send

from backend.graph.state import GraphState
from backend.graph.nodes.query_rewriter import query_rewriter_node
from backend.graph.nodes.decomposer import decomposer_node
from backend.graph.nodes.classifier import classifier_node
from backend.graph.nodes.retrieval_node import retrieval_node
from backend.graph.nodes.grader import grader_node
from backend.graph.nodes.generator import generator_node
from backend.graph.nodes.sub_query_processor import sub_query_processor_node
from backend.tools.sql_tool import sql_tool_node


def route_after_decomposer(state: GraphState):
    if state["query_type"] == "single":
        return "classifier"
    return [
        Send("sub_query_processor", {**state, "original_query": sub_query, "rewritten_query": sub_query})
        for sub_query in state["sub_queries"]
    ]


def route_after_classifier(state: GraphState) -> str:
    category = state["category"]
    if category == "chitchat":
        return "chitchat"
    if category == "policy":
        return "retrieval"
    return "sql_tool"


builder = StateGraph(GraphState)

builder.add_node("query_rewriter",      query_rewriter_node)
builder.add_node("decomposer",          decomposer_node)
builder.add_node("classifier",          classifier_node)
builder.add_node("sub_query_processor", sub_query_processor_node)
builder.add_node("retrieval",           retrieval_node)
builder.add_node("grader",              grader_node)
builder.add_node("sql_tool",            sql_tool_node)
builder.add_node("generator",           generator_node)

builder.add_edge(START,            "query_rewriter")
builder.add_edge("query_rewriter", "decomposer")

builder.add_conditional_edges("decomposer", route_after_decomposer, ["classifier", "sub_query_processor"])

builder.add_conditional_edges(
    "classifier",
    route_after_classifier,
    {
        "chitchat":  "generator",
        "retrieval": "retrieval",
        "sql_tool":  "sql_tool",
    },
)

builder.add_edge("sub_query_processor", "generator")
builder.add_edge("retrieval",           "grader")
builder.add_edge("grader",              "generator")
builder.add_edge("sql_tool",            "generator")
builder.add_edge("generator",           END)

graph = builder.compile()


if __name__ == "__main__":
    from config.settings import redis_client

    TEST_THREAD = "test-graph-thread"
    redis_client.delete(f"history:{TEST_THREAD}")

    def make_state(query: str) -> GraphState:
        return {
            "emp_id": 5, "role": "employee", "manager_id": 2,
            "department": "Engineering", "thread_id": TEST_THREAD,
            "original_query": query, "rewritten_query": "",
            "category": "", "query_type": "", "data_type": None,
            "target_name": "", "sub_queries": None,
            "retrieved_chunks": None, "sub_results": [], "final_response": None,
        }

    test_cases = [
        ("Chitchat", "Hello, how are you?"),
        ("Policy",   "What is the maternity leave policy?"),
        ("Personal", "What is my total leave balance?"),
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
