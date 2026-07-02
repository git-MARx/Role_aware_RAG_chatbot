import json
from config.settings import redis_client

HISTORY_WINDOW = 20


def get_history(thread_id: str) -> list[dict]:
    key = f"history:{thread_id}"
    raw_messages = redis_client.lrange(key, -HISTORY_WINDOW, -1)
    return [json.loads(m) for m in raw_messages]


def save_message(thread_id: str, role: str, content: str) -> None:
    key = f"history:{thread_id}"
    message = json.dumps({"role": role, "content": content})
    redis_client.rpush(key, message)
    redis_client.ltrim(key, -HISTORY_WINDOW, -1)