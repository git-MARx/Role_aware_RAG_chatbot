from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from backend.graph.state import GraphState
from backend.memory.redis_history import save_message
from backend.repository.prompts import SQL_GENERATOR_PROMPT, RETRIEVAL_GENERATOR_PROMPT
from config.settings import LLM_MODEL

load_dotenv()

llm = ChatGroq(model=LLM_MODEL)

def _fmt_applications(rows: list[dict]) -> str:
    if not rows:
        return "_No applications found._"
    headers = ["ID", "Leave Type", "Start", "End", "Days", "Reason", "Applied On", "Status"]
    keys    = ["id", "leave_type", "start_date", "end_date", "working_days", "reason", "applied_on", "status"]
    lines   = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "—")) for k in keys) + " |")
    return "\n".join(lines)


def _fmt_approvals(rows: list[dict]) -> str:
    if not rows:
        return "_No pending approvals._"
    headers = ["ID", "Employee", "Leave Type", "Start", "End", "Days", "Reason", "Applied On"]
    keys    = ["id", "employee_name", "leave_type", "start_date", "end_date", "working_days", "reason", "applied_on"]
    lines   = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(k, "—")) for k in keys) + " |")
    return "\n".join(lines)


FIELD_LABELS: dict[str, str] = {
    "leave_type":     "leave type (PL or GL)",
    "start_date":     "start date (YYYY-MM-DD)",
    "end_date":       "end date (YYYY-MM-DD)",
    "reason":         "reason for leave",
    "application_id": "application ID",
}


def _build_context(sub_results: list[dict]) -> tuple[str, str]:
    types = {item["type"] for item in sub_results}

    if types == {"policy"}:
        chunks = []
        for item in sub_results:
            for c in item["data"]:
                chunks.append(f"Source: {c['source']} | Page: {c['page_label']}\n{c['content']}")
        return "policy", "\n\n".join(chunks)

    sections = []
    for item in sub_results:
        if item["type"] == "sql":
            sections.append(f"[{item['query']}]\n{item['data']}")
        elif item["type"] == "policy":
            excerpts = "\n".join(
                f"  [{c['source']} p.{c['page_label']}] {c['content']}"
                for c in item["data"]
            )
            sections.append(f"[{item['query']}]\n{excerpts}")
        elif item["type"] == "other":
            sections.append(f"[{item['query']}]\n{item['data']}")
    return "sql", "\n\n".join(sections)


def generator_node(state: GraphState) -> dict:
    query       = state["rewritten_query"] or state["original_query"]
    sub_results = state.get("sub_results") or []
    thread_id   = state["thread_id"]

    action_items     = [r for r in sub_results if r.get("type") == "action"]
    non_action_items = [r for r in sub_results if r.get("type") != "action"]

    parts = []

    # Action results
    for item in action_items:
        if item["status"] == "complete":
            data = item["data"]
            if isinstance(data, dict) and "message" in data:
                parts.append(data["message"])
            elif isinstance(data, dict) and data.get("success") is False:
                parts.append(f"Could not complete the request: {data.get('reason', 'unknown error')}")
            elif isinstance(data, dict) and "my_applications" in data:
                sections = ["### My Leave Applications\n" + _fmt_applications(data.get("my_applications") or [])]
                pending = data.get("pending_approvals") or []
                if pending:
                    sections.append("### Pending Approvals\n" + _fmt_approvals(pending))
                parts.append("\n\n".join(sections))
            elif isinstance(data, list):
                if not data:
                    parts.append("_No results found._")
                elif data and "employee_name" in data[0]:
                    parts.append(_fmt_approvals(data))
                else:
                    parts.append(_fmt_applications(data))
        else:
            field = item["missing"][0]
            parts.append(f"To proceed, I need one more detail — what is the {FIELD_LABELS.get(field, field)}?")

    # Non-action results — use LLM
    if non_action_items:
        prompt_type, context = _build_context(non_action_items)
        if prompt_type == "policy":
            prompt = RETRIEVAL_GENERATOR_PROMPT.format(query=query, context=context)
        else:
            prompt = SQL_GENERATOR_PROMPT.format(query=query, context=context)
        response = llm.invoke([HumanMessage(content=prompt)])
        parts.append(response.content.strip())
    elif not action_items:
        # chitchat
        response = llm.invoke([HumanMessage(content=query)])
        parts.append(response.content.strip())

    final_response = "\n\n".join(parts)

    save_message(thread_id, "user", query)
    save_message(thread_id, "assistant", final_response)

    return {"final_response": final_response}


if __name__ == "__main__":
    from config.settings import redis_client

    TEST_THREAD = "test-generator-thread"
    redis_client.delete(f"history:{TEST_THREAD}")

    def make_state(query: str, sub_results: list = None) -> GraphState:
        return {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": TEST_THREAD,
            "original_query": query, "rewritten_query": query,
            "category": "", "query_type": "single", "data_type": None,
            "target_name": "", "sub_queries": None,
            "sub_results": sub_results or [],
            "retrieved_chunks": None, "final_response": None,
        }

    # ── Test 0: other class ───────────────────────────────────────────
    result = generator_node(make_state(
        query="What is capital of india?",
        sub_results=[{"query": "What is capital of india?", "type": "other", "data": "This is not HR bot related query"}],
    ))
    print("Test 0: other class")
    print(f"  {result['final_response']}")
    print("-" * 60)

    # ── Test 1: SQL — single intent ───────────────────────────────────────────
    result = generator_node(make_state(
        query="What is my leave balance?",
        sub_results=[{"query": "What is my leave balance?", "type": "sql", "data": {"PL": 12, "GL": 8}}],
    ))
    print("Test 1 — SQL single")
    print(f"  {result['final_response']}")
    print("-" * 60)

    # ── Test 2: Policy — single intent ───────────────────────────────────────
    result = generator_node(make_state(
        query="How many days of maternity leave am I entitled to?",
        sub_results=[{
            "query": "How many days of maternity leave am I entitled to?",
            "type": "policy",
            "data": [
                {"content": "Female employees are entitled to 26 weeks of paid maternity leave.", "source": "leavepolicy", "page_label": 3},
                {"content": "Maternity leave can be availed 8 weeks before the expected delivery date.", "source": "leavepolicy", "page_label": 4},
            ],
        }],
    ))
    print("Test 2 — Policy single")
    print(f"  {result['final_response']}")
    print("-" * 60)

    # ── Test 3: SQL + Policy — multi intent ──────────────────────────────────
    result = generator_node(make_state(
        query="What is my leave balance and what is the maternity leave policy?",
        sub_results=[
            {"query": "What is my leave balance?", "type": "sql", "data": {"PL": 12, "GL": 8}},
            {
                "query": "What is the maternity leave policy?",
                "type": "policy",
                "data": [{"content": "Female employees are entitled to 26 weeks of paid maternity leave.", "source": "leavepolicy", "page_label": 3}],
            },
        ],
    ))
    print("Test 3 — SQL + Policy multi")
    print(f"  {result['final_response']}")
    print("-" * 60)

    # ── Test 4: Chitchat — empty sub_results ─────────────────────────────────
    result = generator_node(make_state(query="Hello, how are you?"))
    print("Test 4 — Chitchat")
    print(f"  {result['final_response']}")
    print("-" * 60)

    redis_client.delete(f"history:{TEST_THREAD}")
