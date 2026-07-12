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
    thread_id:  str

    # ── Query lifecycle ────────────────────────────────────────────────────────
    original_sub_query:  str

    # ── Classifier output ─────────────────────────────────────────────────────
    category:    str
    data_type:   Optional[str]
    target_name: Optional[str]
    action_type:   Optional[str]
    action_params: Optional[dict]

    # ── Pending action context (injected from parent when continuing a slot-fill)
    pending_action: Optional[dict]

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
    thread_id:  Annotated[str, _last]

    # ── Query lifecycle ────────────────────────────────────────────────────────
    original_query:  str            # raw user input
    rewritten_query: str             # after query rewriter

    # ── Decomposer output ─────────────────────────────────────────────────────
    query_type:  str                 # "single" | "multi"
    sub_queries: list[str]

    # ── Accumulated results across branches ───────────────────────────────────
    sub_results: Annotated[list[dict], operator.add]

    # ── Pending action slot state (loaded from Redis at start of each turn) ─────
    pending_action: Annotated[Optional[dict], _last]

    # ── Final output ──────────────────────────────────────────────────────────
    final_response: Optional[str]
