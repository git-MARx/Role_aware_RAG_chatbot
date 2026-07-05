import operator
from typing import Optional
from typing_extensions import Annotated, TypedDict


def _last(a, b):
    return b


class GraphState(TypedDict):
    # ── Injected from session at request time — never from user input ──────────
    emp_id:     int
    role:       str
    manager_id: Optional[int]
    department: str
    thread_id:  str

    # ── Query lifecycle ────────────────────────────────────────────────────────
    original_query:  str             # raw user input
    rewritten_query: str             # after query rewriter

    # ── Decomposer output ─────────────────────────────────────────────────────
    query_type:  str                 # "single" | "multi"
    sub_queries: Optional[list[str]]

    # ── Classifier output ─────────────────────────────────────────────────────
    category:    Annotated[str,           _last]  # "personal" | "policy" | "chitchat" | "someone_else"
    data_type:   Annotated[Optional[str], _last]  # "leave_by_type" | "total_leave" | "payslip" | None
    target_name: Annotated[Optional[str], _last]

    # ── Intermediate retrieval (within a branch) ───────────────────────────────
    retrieved_chunks: Optional[list[dict]]

    # ── Accumulated results across branches ───────────────────────────────────
    sub_results: Annotated[list[dict], operator.add]

    # ── Final output ──────────────────────────────────────────────────────────
    final_response: Optional[str]
