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


def get_pending_action(thread_id: str) -> dict | None:
    raw = redis_client.get(f"pending_action:{thread_id}")
    return json.loads(raw) if raw else None


def set_pending_action(thread_id: str, action: dict) -> None:
    redis_client.set(f"pending_action:{thread_id}", json.dumps(action))


def clear_pending_action(thread_id: str) -> None:
    redis_client.delete(f"pending_action:{thread_id}")