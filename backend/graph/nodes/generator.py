from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

from backend.graph.state import GraphState
from backend.memory.redis_history import save_message
from backend.repository.prompts import SQL_GENERATOR_PROMPT, RETRIEVAL_GENERATOR_PROMPT
from config.settings import LLM_MODEL

load_dotenv()

llm = ChatGroq(model=LLM_MODEL)


def generator_node(state: GraphState) -> dict:
    query            = state["rewritten_query"]
    sql_result       = state.get("sql_result")
    retrieved_chunks = state.get("retrieved_chunks")
    thread_id        = state["thread_id"]
    category         = state["category"] 

    if sql_result:
        prompt = SQL_GENERATOR_PROMPT.format(
            query=query,
            context=str(sql_result),
        )

    elif retrieved_chunks:
        context = "\n\n".join([
            f"Source: {chunk['source']} | Page: {chunk['page_label']}\n{chunk['content']}"
            for chunk in retrieved_chunks
        ])
        prompt = RETRIEVAL_GENERATOR_PROMPT.format(
            query=query,
            context=context,
        )
    elif category=='chitchat':
        prompt = query
    else:
        return {"final_response": "I'm sorry, I couldn't find any relevant information for your query."}

    response = llm.invoke([HumanMessage(content=prompt)])
    final_response = response.content.strip()

    save_message(thread_id, "user", query)
    save_message(thread_id, "assistant", final_response)

    return {"final_response": final_response}


if __name__ == "__main__":
    from config.settings import redis_client

    TEST_THREAD = "test-generator-thread"
    redis_client.delete(f"history:{TEST_THREAD}")

    def make_state(query, sql_result=None, retrieved_chunks=None, category='') -> GraphState:
        return {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": TEST_THREAD,
            "original_query": query, "rewritten_query": query,
            "category": category, "query_type": "single", "data_type": None,
            "target_name": "", "sub_queries": None,
            "sql_result": sql_result,
            "retrieved_chunks": retrieved_chunks,
            "final_response": None,
        }

    # ── Test 1: SQL path ──────────────────────────────────────────────────────
    result = generator_node(make_state(
        query="What is my leave balance?",
        sql_result={"PL": 12, "GL": 8},
    ))
    print("Test 1 — SQL path")
    print(f"  {result['final_response']}")
    print("-" * 60)

    # ── Test 2: Retrieval path ────────────────────────────────────────────────
    result = generator_node(make_state(
        query="How many days of maternity leave am I entitled to?",
        retrieved_chunks=[
            {
                "content": "Female employees are entitled to 26 weeks of paid maternity leave.",
                "source": "leavepolicy",
                "page_label": 3,
                "score": 0.91,
            },
            {
                "content": "Maternity leave can be availed 8 weeks before the expected delivery date.",
                "source": "leavepolicy",
                "page_label": 4,
                "score": 0.87,
            },
        ],
    ))
    print("Test 2 — Retrieval path")
    print(f"  {result['final_response']}")
    print("-" * 60)
    # ── Test 3: chitcat ─────────────────────────────────────────
    result = generator_node(make_state(category='chitchat',
                                       query="Hello, how are you?"))
    print("Test 3 — chitchat")
    print(f"  {result['final_response']}")
    print("-" * 60)
    # ── Test 4: Fallback — both empty ─────────────────────────────────────────
    result = generator_node(make_state(query="Something unclear"))
    print("Test 4 — Fallback (both sql_result and retrieved_chunks are None)")
    print(f"  {result['final_response']}")
    print("-" * 60)

    redis_client.delete(f"history:{TEST_THREAD}")
