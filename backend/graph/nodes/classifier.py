import json
from datetime import date

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.graph.state import SubQueryState
from backend.repository.prompts import CLASSIFIER_SYSTEM_PROMPT
from config.settings import LLM_MODEL

load_dotenv()

llm = ChatGroq(model=LLM_MODEL)


def classifier_node(state: SubQueryState) -> dict:
    messages = [
        SystemMessage(content=CLASSIFIER_SYSTEM_PROMPT + "\n\nReturn your answer as a JSON object only, no explanation."),
        HumanMessage(content=f"Today is {date.today().isoformat()}.\n\nQuery: {state['original_sub_query']}"),
    ]

    response = llm.invoke(messages)
    text = response.content.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        parsed = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        parsed = {}

    return {
        "category":      parsed.get("category", "other"),
        "target_name":   parsed.get("target_name"),
        "data_type":     parsed.get("data_type"),
        "action_type":   parsed.get("action_type"),
        "action_params": parsed.get("action_params") or {},
    }


if __name__ == "__main__":
    test_queries = [
        "What is my PL leave balance?",
        "am i eligible for maternity leave?",
        "What is the maternity leave policy?",
        "What is Rohan's attendance record?",
        "hi",
        "what is capital of india?",
        "what is price of my samsung s20 fe",
        "waht is langchain"
    ]

    for query in test_queries:
        mock_state: SubQueryState = {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "original_sub_query": query, "category": "", "data_type": None,
            "target_name": "", "retrieved_chunks": None, "sub_results": [],
        }
        result = classifier_node(mock_state)
        print(f"Query      : {query}")
        print(f"Category   : {result['category']}")
        print(f"Targetname : {result['target_name']}")
        print(f"data_type  : {result['data_type']}")
        print("-" * 60)
