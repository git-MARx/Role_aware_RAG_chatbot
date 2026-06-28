from sqlalchemy import create_engine, text

DB_URL = "postgresql+psycopg2://rahularya@localhost:5432/hr_chatbot"

engine = create_engine(DB_URL)

try:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("Connection successful.")
except Exception as e:
    print(f"Connection failed: {e}")
