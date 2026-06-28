from pathlib import Path

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceBgeEmbeddings
from langchain_chroma import Chroma

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR         = Path(__file__).parent.parent.parent
POLICIES_DIR     = BASE_DIR / "data" / "policies"
VECTOR_STORE_DIR = BASE_DIR / "data" / "vector_store"

# ── Config ─────────────────────────────────────────────────────────────────────
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"
COLLECTION_NAME = "hr_policies"
CHUNK_SIZE      = 800
CHUNK_OVERLAP   = 150


def load_documents():
    docs = []
    for pdf in sorted(POLICIES_DIR.glob("*.pdf")):
        loader = PyPDFLoader(str(pdf))
        pages  = loader.load()
        for page in pages:
            page.metadata["source"] = pdf.stem   # e.g. "leavepolicy"
        docs.extend(pages)
        print(f"  Loaded {pdf.name} ({len(pages)} pages)")
    return docs


def split_documents(docs):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )
    chunks = splitter.split_documents(docs)
    print(f"  Split into {len(chunks)} chunks")
    return chunks


def build_vector_store(chunks):
    embeddings = HuggingFaceBgeEmbeddings(
        model_name=EMBEDDING_MODEL,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # Delete existing collection before re-ingesting to avoid duplicates
    client = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(VECTOR_STORE_DIR),
    )
    client.delete_collection()
    print(f"  Deleted existing collection '{COLLECTION_NAME}'")

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=str(VECTOR_STORE_DIR),
    )
    print(f"  Stored {vector_store._collection.count()} vectors in {VECTOR_STORE_DIR}")
    return vector_store


def main():
    print("Loading PDFs...")
    docs = load_documents()

    print("Splitting into chunks...")
    chunks = split_documents(docs)

    print("Embedding and storing in ChromaDB...")
    build_vector_store(chunks)

    print("Ingestion complete.")


if __name__ == "__main__":
    main()
