from typing import List

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from backend.graph.state import GraphState
from backend.repository.prompts import GRADER_SYSTEM_PROMPT
from config.settings import LLM_MODEL

load_dotenv()


class GraderOutput(BaseModel):
    grades: List[int]


llm = ChatGroq(model=LLM_MODEL)
structured_llm = llm.with_structured_output(GraderOutput)


def grader_node(state: GraphState) -> dict:
    query  = state["original_query"]
    chunks = state["retrieved_chunks"] or []

    numbered = "\n\n".join(
        f"Chunk {i+1}:\n{c['content']}"
        for i, c in enumerate(chunks)
    )

    messages = [
        SystemMessage(content=GRADER_SYSTEM_PROMPT),
        HumanMessage(content=f"Query: {query}\n\n{numbered}"),
    ]

    result: GraderOutput = structured_llm.invoke(messages)

    graded_chunks = [chunks[i] for i, v in enumerate(result.grades) if v]

    return {"sub_results": [{"query": query, "type": "policy", "data": graded_chunks}]}


if __name__ == "__main__":
    from backend.graph.nodes.retrieval_node import retrieval_node

    test_queries = [
        "How many days of maternity leave am I entitled to?",
        "What is the policy for working from home?",
    ]

    def make_state(query: str) -> GraphState:
        return {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "department": "Engineering", "thread_id": "test",
            "original_query": query, "rewritten_query": query,
            "category": "policy", "query_type": "single",
            "data_type": None, "target_name": "",
            "sub_queries": None, "retrieved_chunks": None,
            "sub_results": [], "final_response": None,
        }

    for query in test_queries:
        state = make_state(query)
        state.update(retrieval_node(state))
        result = grader_node(state)
        entry = result["sub_results"][0]
        print(f"Query  : {query}")
        print(f"Kept   : {len(entry['data'])} / {len(state['retrieved_chunks'])} chunks")
        print("-" * 60)
