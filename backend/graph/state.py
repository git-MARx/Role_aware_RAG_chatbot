from typing import Optional, Dict
from typing_extensions import TypedDict


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

    # ── Classifier output ──────────────────────────────────────────────────────
    category:   str                  # "personal" | "policy" | "chitchat" | "someone_else"
    query_type: str                  # "single" | "multi"
    data_type:  str                  # "leave_by_type" | "total_leave" | "payslip" | None
    target_name: str

    # ── Decomposer output (only when query_type = "multi") ────────────────────
    sub_queries: Optional[list[str]]

    # ── Tool outputs ───────────────────────────────────────────────────────────
    sql_result:       Optional[Dict]
    retrieved_chunks: Optional[list[dict]]

    # ── Final output ───────────────────────────────────────────────────────────
    final_response: Optional[str]
