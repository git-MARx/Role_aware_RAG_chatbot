from pathlib import Path

from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceBgeEmbeddings

from backend.graph.state import SubQueryState
from config.settings import EMBEDDING_MODEL

BASE_DIR         = Path(__file__).parent.parent.parent.parent
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"
COLLECTION_NAME  = "hr_policies"
TOP_K            = 3

embeddings = HuggingFaceBgeEmbeddings(
    model_name=EMBEDDING_MODEL,
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)

vector_store = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=str(VECTOR_STORE_DIR),
)


def retrieval_node(state: SubQueryState) -> dict:
    query = state["original_sub_query"]

    docs = vector_store.similarity_search_with_score(query, k=TOP_K)

    chunks = [
        {
            "content":    doc.page_content,
            "source":     doc.metadata.get("source", "unknown"),
            "page_label": doc.metadata.get("page", "unknown"),
            "score":      score
        }
        for doc,score in docs
    ]

    return {"retrieved_chunks": chunks}


if __name__ == "__main__":
    test_queries = [
        "How many days of maternity leave am I entitled to?",
        "What is the reimbursement policy for travel?",
        "How many days notice do I need to give before resigning?",
    ]

    def make_state(query: str) -> SubQueryState:
        return {
            "emp_id": 1, "role": "employee", "manager_id": None,
            "original_sub_query": query, "category": "policy", 
            "data_type": None, "target_name": "",
            "retrieved_chunks": None, "sub_results": [],
        }

    for query in test_queries:
        result = retrieval_node(make_state(query))
        print(f"Query: {query}")
        for i, chunk in enumerate(result["retrieved_chunks"], 1):
            print(f"  Chunk {i} | source: {chunk['source']} | page: {chunk['page_label']} | score:{chunk['score']}" )
            print(f"    {chunk['content'][:200].strip()}...")
        print("-" * 60)
