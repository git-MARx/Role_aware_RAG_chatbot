import redis
from sqlalchemy import create_engine

DB_URL      = "postgresql+psycopg2://rahularya@localhost:5432/hr_chatbot"
SESSION_TTL = 900  # 15 minutes in seconds (sliding)

# ── LLM ───────────────────────────────────────────────────────────────────────
LLM_MODEL       = "llama-3.3-70b-versatile"
# LLM_MODEL       = "llama-3.1-8b-instant"
EMBEDDING_MODEL = "BAAI/bge-base-en-v1.5"

engine = create_engine(DB_URL)

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
)
