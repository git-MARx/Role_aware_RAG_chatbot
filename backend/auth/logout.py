from fastapi import APIRouter, Header, HTTPException

from config.settings import redis_client

router = APIRouter()


@router.post("/logout")
def logout(authorization: str = Header(...)):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid token format")

    token = authorization.removeprefix("Bearer ")
    redis_client.delete(f"session:{token}")

    return {"message": "Logged out successfully"}
