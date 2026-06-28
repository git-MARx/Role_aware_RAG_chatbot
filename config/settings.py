import redis
from sqlalchemy import create_engine

DB_URL    = "postgresql+psycopg2://rahularya@localhost:5432/hr_chatbot"
SESSION_TTL = 900  # 15 minutes in seconds (sliding)

engine = create_engine(DB_URL)

redis_client = redis.Redis(
    host="localhost",
    port=6379,
    db=0,
    decode_responses=True,
)
