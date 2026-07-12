import os

from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.dependencies import get_current_employee
from backend.graph.graph import graph
from backend.graph.state import GraphState
from config.logger import log_request, log_error

load_dotenv()

router = APIRouter()

_langfuse_handler = None
if os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY"):
    from langfuse.langchain import CallbackHandler
    _langfuse_handler = CallbackHandler()


class ChatRequest(BaseModel):
    message: str


@router.post("/chat")
def chat(request: ChatRequest, employee: dict = Depends(get_current_employee)):
    state: GraphState = {
        "emp_id":     employee["emp_id"],
        "role":       employee["role"],
        "manager_id": employee["manager_id"],
        "department": employee["department"],
        "thread_id":  employee["thread_id"],

        "original_query":  request.message,
        "rewritten_query": "",
        "query_type":      "",
        "sub_queries":     None,
        "sub_results":     [],
        "pending_action":  None,
        "final_response":  None,
    }

    try:
        config = {
            "callbacks": [_langfuse_handler],
            "metadata": {
                "langfuse_user_id":    str(employee["emp_id"]),
                "langfuse_session_id": employee["thread_id"],
            },
        } if _langfuse_handler else {}
        result = graph.invoke(state, config=config)

        log_request(
            emp_id=employee["emp_id"],
            thread_id=employee["thread_id"],
            original_query=request.message,
            rewritten_query=result.get("rewritten_query", ""),
            query_type=result.get("query_type", ""),
            sub_results=result.get("sub_results", []),
            final_response=result.get("final_response", ""),
        )

        return {"response": result["final_response"]}

    except Exception as e:
        log_error(
            emp_id=employee["emp_id"],
            thread_id=employee["thread_id"],
            original_query=request.message,
            error=e,
        )
        raise HTTPException(status_code=500, detail="Something went wrong, please try again.")
