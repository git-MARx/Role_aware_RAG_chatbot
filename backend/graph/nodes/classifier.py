from typing import Literal, Optional

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from backend.graph.state import GraphState
from backend.repository.prompts import CLASSIFIER_SYSTEM_PROMPT

load_dotenv()


class Classification(BaseModel):
    category:    Literal["personal", "policy", "chitchat", "someone_else"]
    query_type:  Literal["single", "multi"]
    data_type:   Optional[Literal["leave_by_type", "total_leave", "payslip"]]
    target_name: Optional[str]


llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")
structured_llm = llm.with_structured_output(Classification)


def classifier_node(state: GraphState) -> dict:
    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT),
        HumanMessage(content=state["rewritten_query"] if state["rewritten_query"] else state["original_query"]),
    ]

    result: Classification = structured_llm.invoke(messages)

    return {
        "category":   result.category,
        "query_type": result.query_type,
        "target_name":result.target_name,
        "data_type":  result.data_type
    }


if __name__ == "__main__":
    test_queries = [
        "What is my PL leave balance?",
        "What is the maternity leave policy?",
        "What is Rohan's attendance record?",
        "What is my leave balance and what is the maternity leave policy?",
        "show me my payslip"
    ]

    for query in test_queries:
        mock_state: GraphState = {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": "test-thread",
            "original_query": query, "rewritten_query": '',
            "category": "", "query_type": "",
            "sub_queries": None, "sql_result": None,
            "retrieved_chunks": None, "final_response": None,
        }
        result = classifier_node(mock_state)
        print(f"Query      : {query}")
        print(f"Category   : {result['category']}")
        print(f"Query type : {result['query_type']}")
        print(f"Targetname : {result['target_name']}")
        print(f"data_type  : {result['data_type']}")
        print("-" * 60)
