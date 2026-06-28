import json

from fastapi import Header, HTTPException

from config.settings import redis_client, SESSION_TTL


def get_current_employee(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.removeprefix("Bearer ")
    key   = f"session:{token}"

    raw = redis_client.get(key)
    if raw is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")

    # Sliding TTL — reset expiry on every request
    redis_client.expire(key, SESSION_TTL)

    return json.loads(raw)
