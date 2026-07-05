from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from backend.graph.state import GraphState
from backend.memory.redis_history import save_message
from backend.repository.prompts import SQL_GENERATOR_PROMPT, RETRIEVAL_GENERATOR_PROMPT
from config.settings import LLM_MODEL

load_dotenv()

llm = ChatGroq(model=LLM_MODEL)


def _build_context(sub_results: list[dict]) -> tuple[str, str]:
    """Returns (prompt_type, context_string). prompt_type is 'sql' or 'policy'."""
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
    return "sql", "\n\n".join(sections)


def generator_node(state: GraphState) -> dict:
    query       = state["rewritten_query"] or state["original_query"]
    sub_results = state.get("sub_results") or []
    thread_id   = state["thread_id"]

    if not sub_results:
        prompt = query  # chitchat — no data fetched
    else:
        prompt_type, context = _build_context(sub_results)
        if prompt_type == "policy":
            prompt = RETRIEVAL_GENERATOR_PROMPT.format(query=query, context=context)
        else:
            prompt = SQL_GENERATOR_PROMPT.format(query=query, context=context)

    response = llm.invoke([HumanMessage(content=prompt)])
    final_response = response.content.strip()

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
