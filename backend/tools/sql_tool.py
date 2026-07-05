from backend.graph.state import GraphState
from backend.service.access_control import check_access
from backend.repository.sql_queries import (
    get_total_leave_balance,
    get_labeled_leave_balance,
    get_payslip,
)


def sql_tool_node(state: GraphState) -> dict:
    emp_id      = state["emp_id"]
    role        = state["role"]
    category    = state["category"]
    data_type   = state["data_type"]
    target_name = state["target_name"]
    query       = state["original_query"]

    def _result(data) -> dict:
        return {"sub_results": [{"query": query, "type": "sql", "data": data}]}

    if category in ("personal", "someone_else") and data_type is None:
        return _result("I don't have access to this information yet.")

    access = check_access(role, category)

    if access == "denied":
        return _result("You don't have permission to view this information.")

    name = target_name if category == "someone_else" else ""

    if data_type == "total_leave":
        result = get_total_leave_balance(access, role, emp_id, name)

    elif data_type == "leave_by_type":
        result = get_labeled_leave_balance(access, role, emp_id, name)

    elif data_type == "payslip":
        result = get_payslip(access, role, emp_id, name)

    else:
        result = None

    if result is None:
        return _result("No data found for your query.")

    return _result(result)


if __name__ == "__main__":
    from backend.repository.sql_queries import _get_emp_id_by_name

    rohan = _get_emp_id_by_name("Rohan Verma")
    priya = _get_emp_id_by_name("Priya Nair")
    meera = _get_emp_id_by_name("Meera Krishnan")

    def make_state(emp_id, role, category, data_type, target_name="") -> GraphState:
        return {
            "emp_id": emp_id, "role": role, "department": "Engineering",
            "manager_id": None, "thread_id": "test",
            "original_query": "What is my leave balance?", "rewritten_query": "",
            "category": category, "query_type": "single",
            "data_type": data_type, "target_name": target_name,
            "sub_queries": None, "retrieved_chunks": None,
            "sub_results": [], "final_response": None,
        }

    cases = [
        ("Personal — total leave",           make_state(rohan, "employee", "personal",     "total_leave")),
        ("Personal — leave by type",         make_state(rohan, "employee", "personal",     "leave_by_type")),
        ("Personal — payslip",               make_state(rohan, "employee", "personal",     "payslip")),
        ("Personal — data_type None guard",  make_state(rohan, "employee", "personal",     None)),
        ("Manager — reportee total leave",   make_state(priya, "manager",  "someone_else", "total_leave",  "Rohan Verma")),
        ("Manager — non-reportee (denied)",  make_state(priya, "manager",  "someone_else", "total_leave",  "Suresh Kumar")),
        ("HR — non-hr employee",             make_state(meera, "hr",       "someone_else", "leave_by_type","Rohan Verma")),
        ("Employee — someone_else (denied)", make_state(rohan, "employee", "someone_else", "total_leave",  "Priya Nair")),
    ]

    for label, state in cases:
        result = sql_tool_node(state)
        print(f"{label}")
        print(f"  sub_results: {result['sub_results']}")
        print("-" * 60)
