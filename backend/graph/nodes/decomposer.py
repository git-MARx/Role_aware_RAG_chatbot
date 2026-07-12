import json

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.graph.state import GraphState
from backend.repository.prompts import DECOMPOSER_SYSTEM_PROMPT
from config.settings import LLM_MODEL

load_dotenv()

llm = ChatGroq(model=LLM_MODEL)


def decomposer_node(state: GraphState) -> dict:
    query = state["rewritten_query"] if state["rewritten_query"] else state["original_query"]
    messages = [
        SystemMessage(content=DECOMPOSER_SYSTEM_PROMPT + "\n\nReturn your answer as a JSON object only, no explanation."),
        HumanMessage(content=query),
    ]

    response = llm.invoke(messages)
    text = response.content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(text)
        return {
            "query_type":  parsed.get("query_type", "single"),
            "sub_queries": parsed.get("sub_queries", [query]),
        }
    except (json.JSONDecodeError, ValueError):
        return {"query_type": "single", "sub_queries": [query]}


if __name__ == "__main__":
    test_queries = [
        "What is my PL and GL leave balance?",
        "What is my leave balance and what is the maternity leave policy?",
        "show me my payslip",
        "compare my leave balance with Rohan's",
    ]

    for query in test_queries:
        mock_state: GraphState = {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": "test-thread",
            "original_query": query, "rewritten_query": query,
            "query_type": "", "sub_queries": [],
            "sub_results": [], "final_response": None,
        }
        result = decomposer_node(mock_state)
        print(f"Query      : {query}")
        print(f"Query type : {result['query_type']}")
        print(f"Sub queries: {result['sub_queries']}")
        print("-" * 60)
