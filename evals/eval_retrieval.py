from pathlib import Path
import json

from backend.graph.state import GraphState
from backend.graph.nodes.retrieval_node import retrieval_node



BASE_DIR         = Path(__file__).parent.parent.parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"
COLLECTION_NAME  = "hr_policies"
TOP_K            = 3

RESULTS_DIR   = Path(__file__).parent / "results"
RESULTS_FILE  = RESULTS_DIR / "retrieval_score.json"

EVAL_QUERIES = [
    "How many days of maternity leave am I entitled to?",
    "What is the reimbursement policy for travel expenses?",
    "How many days notice do I need to give before resigning?",
    "What is the policy for working from home?",
    "How is the annual performance bonus calculated?",
    "What medical insurance coverage is provided to employees?",
    "What is the policy for sick leave?",
    "Can I carry forward unused leave to next year?",
    "What is the code of conduct for workplace behaviour?",
    "How do I apply for paternity leave?",
]


def make_state(query: str) -> GraphState:
    return {
        "emp_id": 1, "role": "employee", "manager_id": None,
        "department": "Engineering", "thread_id": "eval",
        "original_query": query, "rewritten_query": query,
        "category": "policy", "query_type": "single",
        "data_type": None, "target_name": "",
        "sub_queries": None, "sql_result": None,
        "retrieved_chunks": None, "final_response": None,
    }


def run_retrieval() -> list[dict]:
    results = []
    for query in EVAL_QUERIES:
        state = make_state(query)
        output = retrieval_node(state)
        chunks = [
            {
                "rank":             rank,
                "content":          c["content"],
                "source":           c["source"],
                "page":             c["page_label"],
                "retrieval_score":  round(float(c["score"]), 4),
                "relevance":        None,
            }
            for rank, c in enumerate(output["retrieved_chunks"], start=1)
        ]
        results.append({"query": query, "chunks": chunks})
    return results


def precision_at_k(chunks: list[dict], k: int) -> float:
    top = chunks[:k]
    relevant = sum(1 for c in top if c["relevance"] == 1)
    return relevant / k


def reciprocal_rank(chunks: list[dict]) -> float:
    for c in chunks:
        if c["relevance"] == 1:
            return 1.0 / c["rank"]
    return 0.0


def compute_metrics(results: list[dict]) -> None:
    p1_scores, p3_scores, rr_scores = [], [], []

    for entry in results:
        chunks = entry["chunks"]
        if any(c["relevance"] is None for c in chunks):
            print(f"[WARN] relevance not filled for query: {entry['query']!r} — skipping")
            continue
        p1_scores.append(precision_at_k(chunks, 1))
        p3_scores.append(precision_at_k(chunks, 3))
        rr_scores.append(reciprocal_rank(chunks))

    if not p1_scores:
        print("No fully-labelled queries found. Fill in the 'relevance' field (0 or 1) and re-run.")
        return

    n = len(p1_scores)
    print(f"\nMetrics over {n} queries")
    print(f"  MAP@1  : {sum(p1_scores)/n:.3f}")
    print(f"  MAP@3  : {sum(p3_scores)/n:.3f}")
    print(f"  MRR    : {sum(rr_scores)/n:.3f}")

    per_query = [
        {
            "query": results[i]["query"],
            "P@1":   round(p1_scores[i], 4),
            "P@3":   round(p3_scores[i], 4),
            "RR":    round(rr_scores[i], 4),
        }
        for i in range(n)
    ]
    for row in per_query:
        print(f"  [{row['P@1']:.2f} / {row['P@3']:.2f} / {row['RR']:.2f}]  {row['query']}")


if __name__ == "__main__":
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    if not RESULTS_FILE.exists():
        print("retrieval_score.json not found — running retrieval for all queries…")
        results = run_retrieval()
        RESULTS_FILE.write_text(json.dumps(results, indent=2))
        print(f"Saved to {RESULTS_FILE}")
        print("Fill in the 'relevance' key (0 or 1) for each chunk, then re-run to compute metrics.")
    else:
        print(f"Loading {RESULTS_FILE}…")
        results = json.loads(RESULTS_FILE.read_text())
        compute_metrics(results)
