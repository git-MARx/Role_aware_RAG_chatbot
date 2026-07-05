from datetime import datetime
from pathlib import Path

from backend.graph.nodes.query_rewriter import query_rewriter_node
from backend.graph.state import GraphState
from backend.memory.redis_history import save_message
from config.settings import redis_client

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

TEST_THREAD = "eval-rewriter-thread"

# Each case: (label, history, original_query, expected_rewrite)
# history: list of (role, content) tuples — empty list for no history
test_cases = [
    # ── No history → query as-is ──────────────────────────────────────────────
    (
        "No history — leave balance",
        [],
        "What is my leave balance?",
        "What is my leave balance?",
    ),
    (
        "No history — PL days",
        [],
        "How many PL days do I have?",
        "How many PL days do I have?",
    ),
    (
        "No history — payslip (should NOT expand)",
        [],
        "payslip",
        "payslip",
    ),
    (
        "No history — my payslip (should NOT expand)",
        [],
        "my payslip",
        "my payslip",
    ),
    (
        "No history — policy query",
        [],
        "What is the maternity leave policy?",
        "What is the maternity leave policy?",
    ),

    # ── Pronoun resolution ────────────────────────────────────────────────────
    (
        "Pronoun — his payslip (Rohan)",
        [
            ("user",      "What is Rohan's leave balance?"),
            ("assistant", "Rohan has 12 PL and 8 GL days remaining."),
        ],
        "what about his payslip?",
        "What is Rohan's payslip?",
    ),
    (
        "Pronoun — it (maternity leave)",
        [
            ("user",      "Tell me about maternity leave."),
            ("assistant", "Maternity leave is 26 weeks for female employees."),
        ],
        "how long does it last?",
        "How long does maternity leave last?",
    ),
    (
        "Pronoun — can I apply for it (PL)",
        [
            ("user",      "What is the PL policy?"),
            ("assistant", "PL is Privilege Leave, you get 15 days per year."),
        ],
        "can I apply for it now?",
        "Can I apply for PL now?",
    ),

    # ── Context carryover ─────────────────────────────────────────────────────
    (
        "Carryover — and GL? (after PL)",
        [
            ("user",      "What is my PL balance?"),
            ("assistant", "You have 12 PL days remaining."),
        ],
        "and GL?",
        "What is my GL balance?",
    ),
    (
        "Carryover — and payslip? (after Kiran's leave)",
        [
            ("user",      "What is Kiran's leave balance?"),
            ("assistant", "Kiran has 14 PL and 9 GL days remaining."),
        ],
        "and payslip?",
        "What is Kiran's payslip?",
    ),
    (
        "Carryover — what about food? (after travel reimbursement)",
        [
            ("user",      "What is the travel reimbursement policy?"),
            ("assistant", "Travel reimbursement covers flights and hotels up to a limit."),
        ],
        "what about food?",
        "What is the food reimbursement policy?",
    ),

    # ── Payslip over-rewriting failures ──────────────────────────────────────
    (
        "Payslip — short query should stay minimal",
        [
            ("user",      "What is my PL balance?"),
            ("assistant", "You have 12 PL days remaining."),
        ],
        "payslip",
        "What is my payslip?",
    ),
    (
        "Payslip — mohan's payslip should not expand to policy",
        [],
        "mohan's payslip",
        "What is Mohan's payslip?",
    ),

    # ── Name carryover ────────────────────────────────────────────────────────
    (
        "Name carryover — kiran's after mohan",
        [
            ("user",      "What is Mohan's leave balance?"),
            ("assistant", "Mohan has 11 PL and 9 GL days remaining."),
        ],
        "kiran's",
        "What is Kiran's leave balance?",
    ),
    (
        "Name carryover — and sneha? after rohan's PL",
        [
            ("user",      "What is Rohan's PL balance?"),
            ("assistant", "Rohan has 12 PL days remaining."),
        ],
        "and sneha?",
        "What is Sneha's PL balance?",
    ),
]


def make_state(query: str) -> GraphState:
    return {
        "emp_id": 1, "role": "employee", "manager_id": None,
        "department": "Engineering", "thread_id": TEST_THREAD,
        "original_query": query, "rewritten_query": "",
        "category": "", "query_type": "", "data_type": None,
        "target_name": "", "sub_queries": None,
        "sql_result": None, "retrieved_chunks": None, "final_response": None,
    }


def run_eval():
    lines = []
    lines.append(f"Query Rewriter Eval — {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 70)

    for i, (label, history, query, expected) in enumerate(test_cases, 1):
        redis_client.delete(f"history:{TEST_THREAD}")

        for role, content in history:
            save_message(TEST_THREAD, role, content)

        result = query_rewriter_node(make_state(query))
        actual = result["rewritten_query"]

        lines.append(f"\n[{i:02d}] {label}")
        lines.append(f"  Original  : {query}")
        lines.append(f"  Expected  : {expected}")
        lines.append(f"  Actual    : {actual}")
        lines.append(f"  History   : {len(history)} message(s)")
        lines.append("-" * 70)

        print(lines[-5])
        print(lines[-4])
        print(lines[-3])
        print(lines[-2])
        print(lines[-1])

    redis_client.delete(f"history:{TEST_THREAD}")

    output_path = RESULTS_DIR / f"rewriter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    run_eval()
