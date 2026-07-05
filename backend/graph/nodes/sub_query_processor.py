from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, SystemMessage

from backend.graph.state import GraphState
from backend.graph.nodes.classifier import structured_llm, Classification
from backend.graph.nodes.retrieval_node import retrieval_node
from backend.graph.nodes.grader import grader_node
from backend.service.access_control import check_access
from backend.repository.prompts import CLASSIFIER_SYSTEM_PROMPT
from backend.repository.sql_queries import (
    get_total_leave_balance,
    get_labeled_leave_balance,
    get_payslip,
)

load_dotenv()


def _classify(query: str) -> Classification:
    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]
    return structured_llm.invoke(messages)


def _run_sql(state: GraphState, clf: Classification) -> dict:
    emp_id      = state["emp_id"]
    role        = state["role"]
    category    = clf.category
    data_type   = clf.data_type
    target_name = clf.target_name or ""
    query       = state["original_query"]

    if data_type is None:
        return {"query": query, "type": "sql", "data": "I don't have access to this information yet."}

    access = check_access(role, category)
    if access == "denied":
        return {"query": query, "type": "sql", "data": "You don't have permission to view this information."}

    name = target_name if category == "someone_else" else ""

    if data_type == "total_leave":
        result = get_total_leave_balance(access, role, emp_id, name)
    elif data_type == "leave_by_type":
        result = get_labeled_leave_balance(access, role, emp_id, name)
    elif data_type == "payslip":
        result = get_payslip(access, role, emp_id, name)
    else:
        result = None

    data = result if result is not None else "No data found for your query."
    return {"query": query, "type": "sql", "data": data}


def _run_policy(state: GraphState) -> dict:
    retrieved  = retrieval_node(state)
    local_state = {**state, "retrieved_chunks": retrieved["retrieved_chunks"]}
    graded     = grader_node(local_state)
    return graded["sub_results"][0]   # grader already formats the entry


def sub_query_processor_node(state: GraphState) -> dict:
    query = state["rewritten_query"] or state["original_query"]
    clf   = _classify(query)

    if clf.category in ("personal", "someone_else"):
        entry = _run_sql(state, clf)
    elif clf.category == "policy":
        entry = _run_policy(state)
    else:
        return {"sub_results": []}   # chitchat sub-query — contribute nothing

    return {"sub_results": [entry]}


if __name__ == "__main__":
    from backend.repository.sql_queries import _get_emp_id_by_name

    rohan = _get_emp_id_by_name("Rohan Verma")
    meera = _get_emp_id_by_name("Meera Krishnan")

    def make_state(emp_id: int, role: str, query: str) -> GraphState:
        return {
            "emp_id": emp_id, "role": role, "manager_id": None,
            "department": "Engineering", "thread_id": "test",
            "original_query": query, "rewritten_query": query,
            "category": "", "query_type": "multi", "data_type": None,
            "target_name": "", "sub_queries": None,
            "retrieved_chunks": None, "sub_results": [], "final_response": None,
        }

    test_cases = [
        (meera, "hr",  "What is Rohan's GL balance?"),
        (meera, "hr",  "What is Sneha's PL balance?"),
        (rohan, "employee", "What is the maternity leave policy?"),
    ]

    for emp_id, role, query in test_cases:
        result = sub_query_processor_node(make_state(emp_id, role, query))
        print(f"Query      : {query}")
        print(f"sub_results: {result['sub_results']}")
        print("-" * 60)
