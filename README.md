# HR Policy Chatbot

A conversational HR assistant built with LangGraph that lets employees query personal HR data and company policies through a natural language interface.

---

## What It Does

- Employees can ask about their own leave balance, payslips, and attendance
- Managers can query data for their direct reportees
- HR/Admin can access broader employee data based on their role
- Anyone can ask about company policies (maternity leave, holidays, reimbursement rules)

---

## Architecture Overview

```
User Message
    → Query Rewriter (resolves follow-up references via history)
    → Classifier (category + single/multi intent)
    → [Decomposer — only if multi-intent]
    → Routes to:
        ├── Chitchat → LLM Generator
        ├── Personal/Someone Else → Access Check → SQL Tool → LLM Generator
        └── Policy → Retrieval → Reranker → Grader → LLM Generator
                                                  ↓ (if grader fails)
                                         Query Expansion → Retry Retrieval
```

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
│   │   ├── state.py        # LangGraph state definition
│   │   ├── graph.py        # Graph assembly + routing
│   │   └── nodes/          # query_rewriter, classifier, decomposer,
│   │                       # sql_node, retrieval_node, reranker,
│   │                       # grader, query_expander, generator
│   ├── service/
│   │   └── access_control.py   # RBAC + ABAC logic
│   ├── repository/
│   │   └── sql_queries.py      # SQL query templates (no access logic)
│   ├── tools/
│   │   └── sql_tool.py         # LangGraph tool → service → repository
│   ├── memory/
│   │   └── redis_history.py    # Conversation history read/write
│   └── api/
│       └── routes.py           # FastAPI endpoints (chat, login, logout)
├── data/
│   ├── policies/           # Raw policy documents for ingestion
│   └── vector_store/       # Persisted ChromaDB embeddings
└── config/
    └── settings.py         # DB URLs, Redis config, model names
```

---

## Data Sources

- **PostgreSQL** — employee master, leave balances, payslips, attendance, reporting hierarchy
- **ChromaDB** — embedded HR policy documents (leave policy, reimbursement, holiday calendar, HR guidelines)
  - Source: [HR Policy Docs PDF (Kaggle)](https://www.kaggle.com/datasets/harekalrajesh/hr-policy-docs-pdf)

---

## LangGraph State

```python
state = {
    "employee_id",       # from session
    "role",              # from session
    "manager_id",        # from session
    "department",        # from session
    "thread_id",         # for Redis + LangGraph isolation per user
    "original_query",
    "rewritten_query",
    "category",          # chitchat | personal | someone_else | policy
    "query_type",        # single | multi
    "sub_queries",       # populated by decomposer if multi
    "sql_result",
    "retrieved_chunks",
    "final_response",
}
```

---

## Implementation Order

1. DB schema — employee, leave, payslip, attendance, reporting hierarchy tables
2. Auth — login, session creation, session resolution
3. LangGraph state definition
4. Classifier node
5. SQL tool + repository + service layer (access control)
6. Query rewriter node
7. Retrieval pipeline (retrieval → reranker → grader → query expansion)
8. LLM generator node
9. Decomposer node (multi-intent)
10. Redis history integration
11. Graph assembly + routing
12. FastAPI endpoints
13. Frontend chat UI

---

## Design Principles

- Employee ID always comes from session, never from user input
- Access control lives in the service layer — not in SQL queries, not in the LLM
- Repository holds query templates only — no business logic
- Hallucination check only on the retrieval path, not the SQL path
- Query rewriting always happens before classification
- Decomposition only fires when the classifier says `multi`
- Every user is isolated by `thread_id` in both LangGraph and Redis
