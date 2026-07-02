from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from backend.auth.dependencies import get_current_employee
from backend.graph.graph import graph
from backend.graph.state import GraphState
from config.logger import log_request, log_error

router = APIRouter()


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
        "category":        "",
        "query_type":      "",
        "data_type":       None,
        "target_name":     "",
        "sub_queries":     None,
        "sql_result":      None,
        "retrieved_chunks": None,
        "final_response":  None,
    }

    try:
        result = graph.invoke(state)

        log_request(
            emp_id=employee["emp_id"],
            thread_id=employee["thread_id"],
            original_query=request.message,
            rewritten_query=result.get("rewritten_query", ""),
            category=result.get("category", ""),
            query_type=result.get("query_type", ""),
            data_type=result.get("data_type"),
            target_name=result.get("target_name", ""),
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
