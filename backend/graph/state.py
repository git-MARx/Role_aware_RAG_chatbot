import operator
from typing import Optional
from typing_extensions import Annotated, TypedDict


def _last(a,b):
    return b


class SubQueryState(TypedDict):
    # ── Injected from session at request time — never from user input ──────────
    emp_id:     int
    role:       str
    manager_id: Optional[int]

    # ── Query lifecycle ────────────────────────────────────────────────────────
    original_sub_query:  str             # raw user input

    # ── Classifier output ─────────────────────────────────────────────────────
    category:    str            # "personal" | "policy" | "chitchat" | "someone_else"
    data_type:   Optional[str]  # "leave_by_type" | "total_leave" | "payslip" | None
    target_name: Optional[str]

    # ── Intermediate retrieval (within a branch) ───────────────────────────────
    retrieved_chunks: Optional[list[dict]]

    # ── Results within branches ───────────────────────────────────
    sub_results: list[dict]


class GraphState(TypedDict):
    # ── Injected from session at request time — never from user input ──────────
    emp_id:     Annotated[int, _last]
    role:       Annotated[str, _last]
    manager_id: Annotated[Optional[int], _last]
    department: str
    thread_id:  str

    # ── Query lifecycle ────────────────────────────────────────────────────────
    original_query:  str            # raw user input
    rewritten_query: str             # after query rewriter

    # ── Decomposer output ─────────────────────────────────────────────────────
    query_type:  str                 # "single" | "multi"
    sub_queries: list[str]

    # ── Accumulated results across branches ───────────────────────────────────
    sub_results: Annotated[list[dict], operator.add]

    # ── Final output ──────────────────────────────────────────────────────────
    final_response: Optional[str]
