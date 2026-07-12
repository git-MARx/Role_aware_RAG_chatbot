from typing import Optional

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage

from backend.graph.state import SubQueryState
from backend.memory.redis_history import set_pending_action, clear_pending_action
from backend.mcp.client import call_mcp_tool
from config.settings import LLM_MODEL



load_dotenv()

REQUIRED_FIELDS: dict[str, list[str]] = {
    "apply_leave":    ["leave_type", "start_date", "end_date", "reason"],
    "approve_leave":  ["application_id"],
    "decline_leave":  ["application_id", "reason"],
    "get_all_pending": [],
}

DATE_FIELDS = {"start_date", "end_date"}

FIELD_LABELS: dict[str, str] = {
    "leave_type":     "leave type (PL or GL)",
    "start_date":     "start date (YYYY-MM-DD)",
    "end_date":       "end date (YYYY-MM-DD)",
    "reason":         "reason for leave",
    "application_id": "application ID",
}

_llm = ChatGroq(model=LLM_MODEL)


def _extract_field(message: str, field: str) -> Optional[str]:
    response = _llm.invoke([
        SystemMessage(content=(
            "Extract the value of the requested field from the user message. "
            "Return ONLY the extracted value as plain text, nothing else. "
            "For dates, always return in YYYY-MM-DD format. "
            "If the field is not present in the message, return exactly: NULL"
        )),
        HumanMessage(content=f"Field: {FIELD_LABELS.get(field, field)}\nMessage: {message}"),
    ])
    text = response.content.strip()
    return None if text.upper() == "NULL" else text


def action_node(state: SubQueryState) -> dict:
    query        = state["original_sub_query"]
    action_type  = state.get("action_type")
    action_params = state.get("action_params") or {}
    pending      = state.get("pending_action") or {}
    emp_id       = state["emp_id"]
    manager_id   = state["manager_id"]
    thread_id    = state["thread_id"]

    actual_type = action_type or pending.get("type")

    # Continuation turn: extract the single missing field from current message
    if pending and pending.get("missing"):
        missing_field = pending["missing"][0]
        extracted = _extract_field(query, missing_field)
        if extracted:
            action_params[missing_field] = extracted
        elif missing_field not in DATE_FIELDS:
            action_params[missing_field] = "not provided"

    # Merge previously collected fields with current extraction
    collected = {**pending.get("collected", {}), **{k: v for k, v in action_params.items() if v is not None}}

    required = REQUIRED_FIELDS.get(actual_type, [])
    missing  = [f for f in required if not collected.get(f)]

    if missing:
        set_pending_action(thread_id, {
            "type":      actual_type,
            "collected": collected,
            "missing":   missing,
        })
        return {"sub_results": [{
            "query":   query,
            "type":    "action",
            "status":  "pending",
            "missing": missing,
        }]}

    # All fields present — build MCP arguments from collected + session
    args: dict = {**collected}
    if actual_type == "apply_leave":
        args["emp_id"] = emp_id
    if actual_type in ("approve_leave", "decline_leave"):
        args["manager_id"] = emp_id

    try:
        if actual_type == "get_all_pending":
            my_apps = call_mcp_tool("get_my_applications", {"emp_id": emp_id})
            pending = call_mcp_tool("get_pending_approvals", {"manager_id": emp_id})
            if isinstance(my_apps, dict):
                my_apps = [my_apps]
            if isinstance(pending, dict):
                pending = [pending]
            result = {"my_applications": my_apps or [], "pending_approvals": pending or []}
        else:
            result = call_mcp_tool(actual_type, args)
    except Exception:
        clear_pending_action(thread_id)
        raise
    clear_pending_action(thread_id)

    return {"sub_results": [{
        "query":  query,
        "type":   "action",
        "status": "complete",
        "data":   result,
    }]}
