from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from backend.graph.state import GraphState
from backend.repository.prompts import DECOMPOSER_SYSTEM_PROMPT
from config.settings import LLM_MODEL

load_dotenv()


class Decomposition(BaseModel):
    query_type:  Literal["single", "multi"]
    sub_queries: Optional[list[str]]


llm = ChatGroq(model=LLM_MODEL)
structured_llm = llm.with_structured_output(Decomposition)


def decomposer_node(state: GraphState) -> dict:
    messages = [
        SystemMessage(content=DECOMPOSER_SYSTEM_PROMPT),
        HumanMessage(content=state["rewritten_query"] if state["rewritten_query"] else state["original_query"]),
    ]

    result: Decomposition = structured_llm.invoke(messages)

    return {
        "query_type":  result.query_type,
        "sub_queries": result.sub_queries,
    }


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
            "category": "", "query_type": "",
            "sub_queries": None, "sub_results": [],
            "retrieved_chunks": None, "final_response": None,
        }
        result = decomposer_node(mock_state)
        print(f"Query      : {query}")
        print(f"Query type : {result['query_type']}")
        print(f"Sub queries: {result['sub_queries']}")
        print("-" * 60)
