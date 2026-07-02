from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from backend.graph.state import GraphState
from backend.memory.redis_history import get_history
from backend.repository.prompts import QUERY_REWRITER_PROMPT
from config.settings import LLM_MODEL

load_dotenv()

llm = ChatGroq(model=LLM_MODEL)


def query_rewriter_node(state: GraphState) -> dict:
    thread_id      = state["thread_id"]
    original_query = state["original_query"]

    history = get_history(thread_id)

    if not history:
        return {"rewritten_query": original_query}

    history_text = "\n".join(
        f"{msg['role'].capitalize()}: {msg['content']}" for msg in history
    )

    prompt = QUERY_REWRITER_PROMPT.format(
        history=history_text,
        query=original_query,
    )

    response = llm.invoke([HumanMessage(content=prompt)])

    return {"rewritten_query": response.content.strip()}


if __name__ == "__main__":
    from backend.memory.redis_history import save_message
    from config.settings import redis_client

    TEST_THREAD = "test-rewriter-thread"

    def make_state(query: str) -> GraphState:
        return {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": TEST_THREAD,
            "original_query": query, "rewritten_query": "",
            "category": "", "query_type": "", "data_type": None,
            "target_name": "", "sub_queries": None,
            "sql_result": None, "retrieved_chunks": None, "final_response": None,
        }

    # ── Test 1: no history — should return query as-is ────────────────────────
    redis_client.delete(f"history:{TEST_THREAD}")

    result = query_rewriter_node(make_state("What is my leave balance?"))
    print("Test 1 — No history (should return as-is)")
    print(f"  Input   : What is my leave balance?")
    print(f"  Output  : {result['rewritten_query']}")
    print("-" * 60)

    # ── Test 2: with history — dangling reference should be resolved ──────────
    redis_client.delete(f"history:{TEST_THREAD}")
    save_message(TEST_THREAD, "user",      "What is my PL balance?")
    save_message(TEST_THREAD, "assistant", "You have 12 PL days remaining.")

    result = query_rewriter_node(make_state("What about GL?"))
    print("Test 2 — Follow-up with dangling reference")
    print(f"  Input   : What about GL?")
    print(f"  Output  : {result['rewritten_query']}")
    print("-" * 60)

    # ── Test 3: with history — pronoun resolution ─────────────────────────────
    redis_client.delete(f"history:{TEST_THREAD}")
    save_message(TEST_THREAD, "user",      "Can you tell me about Rohan's leave balance?")
    save_message(TEST_THREAD, "assistant", "Rohan has 10 days of leave remaining.")

    result = query_rewriter_node(make_state("What is his payslip for last month?"))
    print("Test 3 — Pronoun resolution (his → Rohan)")
    print(f"  Input   : What is his payslip for last month?")
    print(f"  Output  : {result['rewritten_query']}")
    print("-" * 60)

    # Cleanup
    redis_client.delete(f"history:{TEST_THREAD}")
