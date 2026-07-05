from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from backend.graph.state import GraphState
from backend.repository.prompts import CLASSIFIER_SYSTEM_PROMPT
from config.settings import LLM_MODEL

load_dotenv()


class Classification(BaseModel):
    category:    Literal["personal", "policy", "chitchat", "someone_else"]
    data_type:   Optional[Literal["leave_by_type", "total_leave", "payslip"]]
    target_name: Optional[str]


llm = ChatGroq(model=LLM_MODEL)
structured_llm = llm.with_structured_output(Classification)


def classifier_node(state: GraphState) -> dict:
    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=state["rewritten_query"] if state["rewritten_query"] else state["original_query"]),
    ]

    result: Classification = structured_llm.invoke(messages)

    return {
        "category":   result.category,
        "target_name":result.target_name,
        "data_type":  result.data_type
    }


if __name__ == "__main__":
    test_queries = [
        "What is my PL leave balance?",
        "am i eligible for maternity leave?",
        "What is the maternity leave policy?",
        "What is Rohan's attendance record?",
        "hi",
    ]

    for query in test_queries:
        mock_state: GraphState = {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": "test-thread",
            "original_query": query, "rewritten_query": query,
            "category": "", "query_type": "", "data_type": None,
            "target_name": "", "sub_queries": None,
            "retrieved_chunks": None, "sub_results": [], "final_response": None,
        }
        result = classifier_node(mock_state)
        print(f"Query      : {query}")
        print(f"Category   : {result['category']}")
        print(f"Targetname : {result['target_name']}")
        print(f"data_type  : {result['data_type']}")
        print("-" * 60)
