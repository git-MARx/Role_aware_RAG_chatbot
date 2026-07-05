from backend.graph.nodes.classifier import classifier_node
from backend.graph.state import GraphState

# (query, expected_category)
test_cases = [
    # personal
    ("What is my leave balance?",           "personal"),
    ("How many PL days do I have left?",    "personal"),
    ("Show me my payslip for last month",   "personal"),
    ("What is my GL balance?",              "personal"),
    ("Can I see my attendance record?",     "personal"),
    ("How many leaves have I used this year?", "personal"),
    ("I want to check my salary slip",      "personal"),

    # someone_else
    ("What is Rohan's leave balance?",      "someone_else"),
    ("Show me Priya's payslip",             "someone_else"),
    ("How many leaves does Arjun have?",    "someone_else"),
    ("What is Kiran's PL balance?",         "someone_else"),
    ("Tell me Sunita's attendance",         "someone_else"),

    # policy
    ("What is the maternity leave policy?",             "policy"),
    ("How many days of notice period do I need to give?", "policy"),
    ("What is the reimbursement policy for travel?",    "policy"),
    ("Am I eligible for paternity leave?",              "policy"),
    ("What are the rules for casual leave?",            "policy"),

    # chitchat
    ("Hello, how are you?",      "chitchat"),
    ("Thank you for your help",  "chitchat"),
    ("What can you do?",         "chitchat"),
]

CLASSES = ["personal", "someone_else", "policy", "chitchat"]


def make_state(query: str) -> GraphState:
    return {
        "emp_id": 1, "role": "employee", "manager_id": None,
        "department": "Engineering", "thread_id": "test-thread",
        "original_query": query, "rewritten_query": query,
        "category": "", "query_type": "", "data_type": None,
        "target_name": "", "sub_queries": None,
        "sql_result": None, "retrieved_chunks": None, "final_response": None,
    }


def compute_metrics(y_true: list[str], y_pred: list[str]) -> dict:
    metrics = {}
    for cls in CLASSES:
        tp = sum(t == cls and p == cls for t, p in zip(y_true, y_pred))
        fp = sum(t != cls and p == cls for t, p in zip(y_true, y_pred))
        fn = sum(t == cls and p != cls for t, p in zip(y_true, y_pred))

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall    = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1        = (2 * precision * recall / (precision + recall)
                     if (precision + recall) > 0 else 0.0)
        metrics[cls] = {"precision": precision, "recall": recall, "f1": f1}

    accuracy      = sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true)
    macro_p       = sum(m["precision"] for m in metrics.values()) / len(CLASSES)
    macro_r       = sum(m["recall"]    for m in metrics.values()) / len(CLASSES)
    macro_f1      = sum(m["f1"]        for m in metrics.values()) / len(CLASSES)

    metrics["accuracy"] = accuracy
    metrics["macro"]    = {"precision": macro_p, "recall": macro_r, "f1": macro_f1}
    return metrics


if __name__ == "__main__":
    y_true, y_pred = [], []

    print(f"{'EXPECTED':<15} {'PREDICTED':<15} {'OK':<5} QUERY")
    print("-" * 70)

    for query, expected in test_cases:
        result    = classifier_node(make_state(query))
        predicted = result["category"]
        ok        = "✓" if predicted == expected else "✗"

        print(f"{expected:<15} {predicted:<15} {ok:<5} {query}")
        y_true.append(expected)
        y_pred.append(predicted)

    metrics = compute_metrics(y_true, y_pred)

    print("\n" + "=" * 70)
    print(f"  ACCURACY : {metrics['accuracy']:.2%}")
    print("=" * 70)
    print(f"  {'CLASS':<15} {'PRECISION':>10} {'RECALL':>10} {'F1':>10}")
    print("  " + "-" * 45)
    for cls in CLASSES:
        m = metrics[cls]
        print(f"  {cls:<15} {m['precision']:>10.2%} {m['recall']:>10.2%} {m['f1']:>10.2%}")
    print("  " + "-" * 45)
    m = metrics["macro"]
    print(f"  {'macro avg':<15} {m['precision']:>10.2%} {m['recall']:>10.2%} {m['f1']:>10.2%}")
    print("=" * 70)
