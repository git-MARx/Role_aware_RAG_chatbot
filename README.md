# HR Policy Chatbot

A conversational HR assistant built with LangGraph that lets employees query personal HR data and company policies through a natural language interface.

---

## What It Does

- Employees can ask about their own leave balance, payslips, and attendance
- Managers can query data for their direct reportees
- HR/Admin can access broader employee data based on their role
- Anyone can ask about company policies (maternity leave, holidays, reimbursement rules)
- Multi-intent queries are handled in parallel (e.g. "What's my leave balance and what's the WFH policy?")

---

## Architecture Overview

```
User Message
    → Query Rewriter    (resolves follow-up references via conversation history)
    → Decomposer        (splits into sub-queries; single intent → list of one)
    → Send × N          (fan-out: one subgraph invocation per sub-query)
         └── Subgraph (per sub-query, fully isolated state):
                → Classifier    (category + data_type + target_name)
                → Routes to:
                    ├── Chitchat  → END
                    ├── SQL Tool  → END   (personal / someone_else)
                    └── Retrieval → Grader → END   (policy)
    → Generator         (merges all sub_results → final response)
```

Each subgraph branch runs in isolation — no shared mutable state between parallel branches.

---

## Access Control

Combines RBAC and ABAC:

| Role | Access |
|------|--------|
| Employee | Own data only |
| Manager | Own data + direct reportees |
| HR | Own data + employees under their purview |
| Admin | Everything |

**Key principle:** Employee ID and role always come from the server-side session — never from the user's message.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent framework | LangGraph |
| Structured data | PostgreSQL |
| Policy embeddings | ChromaDB (local persistent) |
| Conversation history | Redis (sliding window, last 20 messages) |
| LLM | Groq (via LangChain ChatGroq) |
| Embeddings | HuggingFace BGE |
| API | FastAPI |
| Auth | Session tokens (server-side) |

---

## Project Structure

```
hr-chatbot/
├── frontend/               # Login page + chat window
├── backend/
│   ├── auth/               # Session management, login/logout
│   ├── graph/
│   │   ├── state.py        # GraphState + SubQueryState definitions
│   │   ├── graph.py        # Graph assembly, subgraph compilation, routing
│   │   └── nodes/          # query_rewriter, decomposer, classifier,
│   │                       # retrieval_node, grader, generator
│   ├── service/
│   │   └── access_control.py   # RBAC + ABAC logic
│   ├── repository/
│   │   ├── sql_queries.py      # SQL query templates (no access logic)
│   │   └── prompts.py          # System prompts for all LLM nodes
│   ├── tools/
│   │   └── sql_tool.py         # SQL tool node (service → repository)
│   ├── memory/
│   │   └── redis_history.py    # Conversation history read/write
│   └── api/
│       └── routes.py           # FastAPI endpoints (chat, login, logout)
├── data/
│   ├── policies/           # Raw policy documents for ingestion
│   └── vector_store/       # Persisted ChromaDB embeddings
├── evals/
│   ├── eval_retrieval.py   # Retrieval evaluation (P@1, P@3, MRR)
│   └── results/            # Scored retrieval results (JSONL)
└── config/
    ├── settings.py         # DB URLs, Redis config, model names
    └── logger.py           # JSONL request + error logging
```

---

## LangGraph State

Two state schemas are used — parent graph and subgraph:

```python
# Parent graph state (shared across the full pipeline)
class GraphState(TypedDict):
    emp_id:          Annotated[int, _last]
    role:            Annotated[str, _last]
    manager_id:      Annotated[Optional[int], _last]
    department:      str
    thread_id:       str
    original_query:  str
    rewritten_query: str
    query_type:      str           # "single" | "multi"
    sub_queries:     list[str]
    sub_results:     Annotated[list[dict], operator.add]   # accumulated across branches
    final_response:  Optional[str]

# Per-branch subgraph state (private to each parallel branch)
class SubQueryState(TypedDict):
    emp_id:             int
    role:               str
    manager_id:         Optional[int]
    original_sub_query: str
    category:           str            # "personal" | "someone_else" | "policy" | "chitchat"
    data_type:          Optional[str]  # "total_leave" | "leave_by_type" | "payslip"
    target_name:        Optional[str]
    retrieved_chunks:   Optional[list[dict]]
    sub_results:        list[dict]
```

---

## sub_results Format

Each branch appends one entry to `sub_results`. The generator reads `type` to route context building.

**SQL branch:**
```python
{
    "query":       str,
    "type":        "sql",
    "category":    str,            # "personal" | "someone_else"
    "data_type":   str,            # "total_leave" | "leave_by_type" | "payslip"
    "target_name": str | None,
    "data":        Any,            # query result or access-denied message
}
```

**Policy branch:**
```python
{
    "query":           str,
    "type":            "policy",
    "retrieved_count": int,        # chunks retrieved before grading
    "graded_count":    int,        # chunks that passed the grader
    "data":            list[dict], # graded chunks with content + metadata
}
```

---

## Data Sources

- **PostgreSQL** — employee master, leave balances, payslips, attendance, reporting hierarchy
- **ChromaDB** — embedded HR policy documents (leave policy, reimbursement, holiday calendar, HR guidelines)
  - Source: [HR Policy Docs PDF (Kaggle)](https://www.kaggle.com/datasets/harekalrajesh/hr-policy-docs-pdf)

---

## Logging

All requests and errors are written as JSONL to `logs/requests_<date>.jsonl` (daily rotation, 3-day retention).

**Request log fields:** `request_id`, `timestamp`, `emp_id`, `thread_id`, `original_query`, `rewritten_query`, `query_type`, `sql_entries` (per-branch metadata + data), `policy_entries` (per-branch retrieved/graded counts), `final_response`

**Error log fields:** `request_id`, `timestamp`, `emp_id`, `thread_id`, `original_query`, `error`, `traceback`

---

## Design Principles

- Employee ID always comes from session, never from user input
- Access control lives in the service layer — not in SQL queries, not in the LLM
- Repository holds query templates only — no business logic
- Parallel sub-queries run in isolated subgraph state — no shared mutable fields between branches
- Decomposer always runs; single-intent queries produce a list of one sub-query
- Classifier runs inside the subgraph, after decomposition, once per sub-query
- Every user is isolated by `thread_id` in both LangGraph and Redis
